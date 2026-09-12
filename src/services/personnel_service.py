"""
========================================================================
DRENAET-RH — PersonnelService
========================================================================
Service métier pour la gestion des agents (Personnel).

Responsabilités :
- CRUD complet (Create / Read / Update / Delete)
- Recherche avec filtres (par matricule, nom, structure, sexe, statut...)
- Statistiques (nombre d'agents par structure, par sexe, par statut...)
- Validation des règles métier (matricule unique, champs obligatoires)
- Intégration avec AuditService pour traçabilité automatique

Note importante sur les sessions SQLAlchemy :
Toutes les méthodes utilisent `with get_session()` pour garantir que
les transactions sont proprement commit ou rollback en cas d'erreur.

Note sur le hard-delete :
Quand un agent est supprimé, ses documents générés (autorisation_absence,
etc.) restent en base mais leur foreign key `personnel_id` est mise à NULL
via `ondelete='SET NULL'` (à configurer dans le modèle DocumentGenere).
"""

from datetime import date, datetime
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.models import get_session, Personnel, Structure
from src.services.audit_service import AuditService


# ========================================================================
# EXCEPTIONS MÉTIER
# ========================================================================
class PersonnelException(Exception):
    """Exception de base pour les erreurs métier du personnel."""
    pass


class MatriculeExistantError(PersonnelException):
    """Le matricule est déjà utilisé par un autre agent."""
    pass


class ChampObligatoireError(PersonnelException):
    """Un champ obligatoire est manquant."""
    pass


class AgentIntrouvableError(PersonnelException):
    """L'agent n'existe pas dans la base."""
    pass


class StructureInvalideError(PersonnelException):
    """La structure référencée n'existe pas."""
    pass


# ========================================================================
# CONSTANTES
# ========================================================================
CHAMPS_OBLIGATOIRES = [
    "matricule",
    "nom",
    "prenoms",
    "sexe",
    "emploi",
    "structure_id",
]

CHAMPS_MODIFIABLES = [
    # Identité
    "nom", "prenoms", "sexe", "date_naissance", "lieu_naissance",
    "situation_matrimoniale",
    # Contact
    "telephone", "email", "residence",
    # Carrière
    "emploi", "grade", "fonction",
    "structure_id",
    "date_prise_service", "date_affectation",
    "statut",
]

SEXES_VALIDES = ["M", "F"]
STATUTS_VALIDES = ["Actif", "Inactif", "En congé", "Muté", "Retraité"]


# ========================================================================
# SERVICE PRINCIPAL
# ========================================================================
class PersonnelService:
    """Service métier pour la gestion du personnel DRENAET."""

    # ====================================================================
    # CREATE
    # ====================================================================
    @staticmethod
    def create(
        data: Dict[str, Any],
        user_login: str = "system",
        user_role: str = None,
        source: str = "MANUAL",
        import_log_id: int = None,
        commentaire: str = None,
    ) -> Dict[str, Any]:
        """
        Crée un nouvel agent.

        Args:
            data: dict des données de l'agent (au moins CHAMPS_OBLIGATOIRES)
            user_login: qui crée l'agent (pour audit)
            user_role: rôle de l'utilisateur (admin, operateur, ...)
            source: "MANUAL" | "IMPORT" | "SYSTEM"
            import_log_id: si source=IMPORT, l'ID de l'import concerné
            commentaire: note optionnelle pour l'audit

        Returns:
            dict représentant l'agent créé (avec son id)

        Raises:
            ChampObligatoireError: si un champ requis est manquant
            MatriculeExistantError: si le matricule est déjà utilisé
            StructureInvalideError: si structure_id n'existe pas
        """
        # 1. Validation des champs obligatoires
        for champ in CHAMPS_OBLIGATOIRES:
            if champ not in data or data[champ] in (None, "", ):
                raise ChampObligatoireError(
                    f"Le champ '{champ}' est obligatoire pour créer un agent."
                )

        # 2. Validation du sexe
        if data.get("sexe") not in SEXES_VALIDES:
            raise ChampObligatoireError(
                f"Le sexe doit être 'M' ou 'F' (reçu : {data.get('sexe')})"
            )

        # 3. Validation du matricule (unicité)
        matricule = str(data["matricule"]).strip().upper()
        data["matricule"] = matricule

        with get_session() as db:
            # Vérifier unicité matricule
            existant = db.query(Personnel).filter_by(matricule=matricule).first()
            if existant:
                raise MatriculeExistantError(
                    f"Le matricule '{matricule}' est déjà utilisé "
                    f"par : {existant.nom_complet}"
                )

            # Vérifier existence structure
            structure = db.query(Structure).filter_by(id=data["structure_id"]).first()
            if not structure:
                raise StructureInvalideError(
                    f"La structure ID={data['structure_id']} n'existe pas."
                )

            # Statut par défaut si non fourni
            data.setdefault("statut", "Actif")

            # Créer l'agent
            agent_kwargs = {
                k: v for k, v in data.items()
                if k in CHAMPS_MODIFIABLES + ["matricule"]
            }
            agent = Personnel(**agent_kwargs)

            try:
                db.add(agent)
                db.flush()
                agent_dict = PersonnelService._to_dict(agent)

                # Audit trail
                AuditService.log_create(
                    db=db,
                    matricule=agent.matricule,
                    nom_complet=agent.nom_complet,
                    valeurs_initiales=agent_dict,
                    user_login=user_login,
                    user_role=user_role,
                    source=source,
                    import_log_id=import_log_id,
                    commentaire=commentaire,
                )

                return agent_dict

            except IntegrityError as e:
                db.rollback()
                raise PersonnelException(
                    f"Erreur d'intégrité SQL : {e.orig}"
                ) from e

    # ====================================================================
    # READ
    # ====================================================================
    @staticmethod
    def get_by_id(agent_id: int) -> Optional[Dict[str, Any]]:
        """Récupère un agent par son ID interne."""
        with get_session() as db:
            agent = db.query(Personnel).filter_by(id=agent_id).first()
            return PersonnelService._to_dict(agent) if agent else None

    @staticmethod
    def get_by_matricule(matricule: str) -> Optional[Dict[str, Any]]:
        """Récupère un agent par son matricule."""
        matricule = str(matricule).strip().upper()
        with get_session() as db:
            agent = db.query(Personnel).filter_by(matricule=matricule).first()
            return PersonnelService._to_dict(agent) if agent else None

    @staticmethod
    def exists_matricule(matricule: str) -> bool:
        """Vérifie si un matricule existe."""
        matricule = str(matricule).strip().upper()
        with get_session() as db:
            return db.query(Personnel).filter_by(matricule=matricule).count() > 0

    @staticmethod
    def count(filters: Dict[str, Any] = None) -> int:
        """Compte le nombre d'agents (avec filtres optionnels)."""
        with get_session() as db:
            q = db.query(Personnel)
            if filters:
                q = PersonnelService._apply_filters(q, filters)
            return q.count()

    @staticmethod
    def search(
        query: str = "",
        filters: Dict[str, Any] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "nom",
        sort_desc: bool = False,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Recherche paginée d'agents.

        Args:
            query: recherche full-text sur matricule / nom / prénoms
            filters: {"structure_id": 1, "sexe": "M", "statut": "Actif"}
            page: numéro de page (1-indexed)
            page_size: agents par page (50 par défaut)
            sort_by: champ de tri (nom, matricule, date_prise_service...)
            sort_desc: True pour tri descendant

        Returns:
            (liste_agents, total_count)
        """
        with get_session() as db:
            q = db.query(Personnel)

            # Filtres
            if filters:
                q = PersonnelService._apply_filters(q, filters)

            # Recherche full-text
            if query and query.strip():
                q_str = f"%{query.strip()}%"
                q = q.filter(
                    or_(
                        Personnel.matricule.ilike(q_str),
                        Personnel.nom.ilike(q_str),
                        Personnel.prenoms.ilike(q_str),
                    )
                )

            # Total avant pagination
            total = q.count()

            # Tri
            sort_col = getattr(Personnel, sort_by, Personnel.nom)
            q = q.order_by(sort_col.desc() if sort_desc else sort_col.asc())

            # Pagination
            offset = max(0, (page - 1)) * page_size
            agents = q.offset(offset).limit(page_size).all()

            return [PersonnelService._to_dict(a) for a in agents], total

    # ====================================================================
    # UPDATE
    # ====================================================================
    @staticmethod
    def update(
        agent_id: int,
        data: Dict[str, Any],
        user_login: str = "system",
        user_role: str = None,
        source: str = "MANUAL",
        import_log_id: int = None,
        commentaire: str = None,
    ) -> Dict[str, Any]:
        """
        Met à jour un agent existant.

        Args:
            agent_id: ID interne de l'agent
            data: dict des champs à modifier (seuls CHAMPS_MODIFIABLES acceptés)
            user_login: qui modifie
            ...

        Returns:
            dict de l'agent après mise à jour

        Raises:
            AgentIntrouvableError: si l'agent n'existe pas
            ChampObligatoireError: si un champ requis devient vide
            StructureInvalideError: si structure_id ne pointe pas vers une struct valide
        """
        with get_session() as db:
            agent = db.query(Personnel).filter_by(id=agent_id).first()
            if not agent:
                raise AgentIntrouvableError(
                    f"Aucun agent trouvé avec l'ID={agent_id}"
                )

            # Vérifier structure si modifiée
            if "structure_id" in data and data["structure_id"] != agent.structure_id:
                structure = db.query(Structure).filter_by(id=data["structure_id"]).first()
                if not structure:
                    raise StructureInvalideError(
                        f"La structure ID={data['structure_id']} n'existe pas."
                    )

            # Détecter les changements et les appliquer
            changements = {}
            for champ, nouvelle_valeur in data.items():
                if champ not in CHAMPS_MODIFIABLES:
                    continue  # ignorer les champs non modifiables (id, matricule...)

                ancienne_valeur = getattr(agent, champ, None)

                # Normaliser pour comparaison (dates, strings)
                if ancienne_valeur != nouvelle_valeur:
                    # Vérifier que les champs obligatoires ne deviennent pas vides
                    if champ in CHAMPS_OBLIGATOIRES and nouvelle_valeur in (None, "", 0):
                        raise ChampObligatoireError(
                            f"Le champ '{champ}' ne peut pas être vide."
                        )

                    changements[champ] = [
                        PersonnelService._serialize_value(ancienne_valeur),
                        PersonnelService._serialize_value(nouvelle_valeur),
                    ]
                    setattr(agent, champ, nouvelle_valeur)

            if not changements:
                # Rien n'a changé, retourner l'agent tel quel
                return PersonnelService._to_dict(agent)

            try:
                db.flush()

                # Audit trail
                AuditService.log_update(
                    db=db,
                    matricule=agent.matricule,
                    nom_complet=agent.nom_complet,
                    changements=changements,
                    user_login=user_login,
                    user_role=user_role,
                    source=source,
                    import_log_id=import_log_id,
                    commentaire=commentaire,
                )

                return PersonnelService._to_dict(agent)

            except IntegrityError as e:
                db.rollback()
                raise PersonnelException(
                    f"Erreur d'intégrité SQL : {e.orig}"
                ) from e

    # ====================================================================
    # DELETE (hard-delete)
    # ====================================================================
    @staticmethod
    def delete(
        agent_id: int,
        user_login: str = "system",
        user_role: str = None,
        commentaire: str = None,
    ) -> Dict[str, Any]:
        """
        Supprime un agent (hard-delete).

        ⚠️ Les documents générés référençant cet agent verront leur
        `personnel_id` mis à NULL grâce à `ondelete='SET NULL'` sur la FK.

        Args:
            agent_id: ID interne de l'agent
            user_login: qui supprime
            commentaire: raison de la suppression (recommandé pour audit)

        Returns:
            Snapshot de l'agent supprimé (pour affichage confirmation)

        Raises:
            AgentIntrouvableError
        """
        with get_session() as db:
            agent = db.query(Personnel).filter_by(id=agent_id).first()
            if not agent:
                raise AgentIntrouvableError(
                    f"Aucun agent trouvé avec l'ID={agent_id}"
                )

            # Snapshot avant suppression
            snapshot = PersonnelService._to_dict(agent)

            # Audit trail AVANT suppression (pour préserver les infos)
            AuditService.log_delete(
                db=db,
                matricule=agent.matricule,
                nom_complet=agent.nom_complet,
                snapshot=snapshot,
                user_login=user_login,
                user_role=user_role,
                commentaire=commentaire,
            )

            # Suppression physique
            db.delete(agent)
            db.flush()

            return snapshot

    # ====================================================================
    # STATISTIQUES
    # ====================================================================
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """
        Retourne un dict de statistiques globales.

        Utilisé par le Dashboard.
        """
        with get_session() as db:
            total = db.query(Personnel).count()

            # Répartition par sexe
            hommes = db.query(Personnel).filter_by(sexe="M").count()
            femmes = db.query(Personnel).filter_by(sexe="F").count()

            # Répartition par statut
            par_statut = dict(
                db.query(Personnel.statut, func.count(Personnel.id))
                .group_by(Personnel.statut)
                .all()
            )

            # Top 5 structures par nombre d'agents
            top_structures = (
                db.query(Structure.nom, func.count(Personnel.id).label("nb"))
                .join(Personnel, Personnel.structure_id == Structure.id)
                .group_by(Structure.nom)
                .order_by(func.count(Personnel.id).desc())
                .limit(5)
                .all()
            )

            return {
                "total_agents": total,
                "hommes": hommes,
                "femmes": femmes,
                "ratio_hommes_pct": round(hommes / total * 100, 1) if total else 0,
                "ratio_femmes_pct": round(femmes / total * 100, 1) if total else 0,
                "par_statut": par_statut,
                "top_structures": [
                    {"structure": nom, "nb_agents": nb} for nom, nb in top_structures
                ],
            }

    # ====================================================================
    # HELPERS PRIVÉS
    # ====================================================================
    @staticmethod
    def _apply_filters(query, filters: Dict[str, Any]):
        """Applique les filtres à une query SQLAlchemy."""
        for champ, valeur in filters.items():
            if valeur in (None, ""):
                continue
            if hasattr(Personnel, champ):
                query = query.filter(getattr(Personnel, champ) == valeur)
        return query

    @staticmethod
    def _to_dict(agent) -> Dict[str, Any]:
        """Convertit un objet Personnel en dict pour l'API/UI."""
        if not agent:
            return None
        return {
            "id": agent.id,
            "matricule": agent.matricule,
            "nom": agent.nom,
            "prenoms": agent.prenoms,
            "nom_complet": agent.nom_complet,
            "sexe": agent.sexe,
            "civilite": agent.civilite,
            "date_naissance": PersonnelService._serialize_value(agent.date_naissance),
            "lieu_naissance": agent.lieu_naissance,
            "situation_matrimoniale": agent.situation_matrimoniale,
            "telephone": agent.telephone,
            "email": agent.email,
            "residence": agent.residence,
            "emploi": agent.emploi,
            "grade": agent.grade,
            "fonction": agent.fonction,
            "structure_id": agent.structure_id,
            "structure_nom": agent.structure.nom if agent.structure else None,
            "structure_type": agent.structure.type if agent.structure else None,
            "date_prise_service": PersonnelService._serialize_value(agent.date_prise_service),
            "date_affectation": PersonnelService._serialize_value(agent.date_affectation),
            "statut": agent.statut,
        }

    @staticmethod
    def _serialize_value(value):
        """Sérialise une valeur pour JSON (dates → ISO)."""
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value