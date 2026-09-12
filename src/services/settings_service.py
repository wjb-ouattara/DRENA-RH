"""
========================================================================
DRENAET-RH — SettingsService
========================================================================
Service de gestion des paramètres modifiables de l'application.

Fonctionnement :
1. Les valeurs par défaut viennent de config/settings.py (DRENAET_INFO)
2. Les valeurs personnalisées sont stockées en BD (table settings)
3. get_all() fusionne : BD (si présent) > défaut (config/settings.py)
4. sync_to_runtime_config() met à jour EN PLACE le dict
   config.settings.DRENAET_INFO, pour que les 8 templates de documents
   (qui lisent settings.DRENAET_INFO à chaque génération) voient
   automatiquement les nouvelles valeurs, SANS modification de leur code.

Clés gérées :
- nom_officiel, ministere, ville, region, bp, telephone, email
- directeur_regional_nom, directeur_regional_titre, directeur_par_procuration
- quota_conges_annuel (jours ouvrés/an, utilisé par AbsenceService)
- logo_path (chemin du logo custom, optionnel)
"""

from typing import Dict, Any, Optional

from src.models import get_session
from src.models.settings_model import Settings


def _get_config_defaults() -> Dict[str, Any]:
    """Récupère les valeurs par défaut depuis config/settings.py."""
    from config import settings as app_config

    info = dict(app_config.DRENAET_INFO)
    return {
        "nom_officiel": info.get("nom_officiel", ""),
        "ministere": info.get("ministere", ""),
        "ville": info.get("ville", "Katiola"),
        "region": info.get("region", "Hambol"),
        "bp": info.get("bp", ""),
        "telephone": info.get("telephone", ""),
        "email": info.get("email", ""),
        "directeur_regional_nom": info.get("directeur_regional_nom", ""),
        "directeur_regional_titre": info.get("directeur_regional_titre", "Directeur Régional"),
        "directeur_par_procuration": str(info.get("directeur_par_procuration", False)),
        "quota_conges_annuel": "30",
        "logo_path": "",
    }


CATEGORIE_MAP = {
    "nom_officiel": "identite", "ministere": "identite", "ville": "identite",
    "region": "identite", "bp": "identite", "telephone": "identite", "email": "identite",
    "directeur_regional_nom": "direction", "directeur_regional_titre": "direction",
    "directeur_par_procuration": "direction",
    "quota_conges_annuel": "documents", "logo_path": "documents",
}


class SettingsService:
    """Service de gestion des paramètres de l'application."""

    # ====================================================================
    @staticmethod
    def get_all() -> Dict[str, Any]:
        """Retourne tous les paramètres, fusionnés (BD > défauts config)."""
        defaults = _get_config_defaults()

        with get_session() as db:
            rows = db.query(Settings).all()
            overrides = {r.cle: r.valeur for r in rows}

        result = dict(defaults)
        result.update({k: v for k, v in overrides.items() if v is not None})
        return result

    # ====================================================================
    @staticmethod
    def get(cle: str, default: Any = None) -> Any:
        """Récupère un paramètre unique."""
        with get_session() as db:
            row = db.query(Settings).filter_by(cle=cle).first()
            if row and row.valeur is not None:
                return row.valeur

        defaults = _get_config_defaults()
        return defaults.get(cle, default)

    # ====================================================================
    @staticmethod
    def update(data: Dict[str, Any], user_login: str = "system") -> Dict[str, Any]:
        """
        Met à jour plusieurs paramètres en une fois.

        Args:
            data: {"cle": "valeur", ...}
            user_login: qui modifie

        Returns:
            Le dict complet des paramètres après mise à jour.
        """
        with get_session() as db:
            for cle, valeur in data.items():
                row = db.query(Settings).filter_by(cle=cle).first()
                if row:
                    row.valeur = str(valeur) if valeur is not None else None
                    row.modifie_par = user_login
                else:
                    row = Settings(
                        cle=cle,
                        valeur=str(valeur) if valeur is not None else None,
                        categorie=CATEGORIE_MAP.get(cle, "autre"),
                        modifie_par=user_login,
                    )
                    db.add(row)
            db.flush()

        SettingsService.sync_to_runtime_config()
        return SettingsService.get_all()

    # ====================================================================
    @staticmethod
    def reset_to_defaults(user_login: str = "system") -> Dict[str, Any]:
        """Supprime tous les overrides BD (retour aux valeurs de config/settings.py)."""
        with get_session() as db:
            db.query(Settings).delete()
            db.flush()

        SettingsService.sync_to_runtime_config()
        return SettingsService.get_all()

    # ====================================================================
    @staticmethod
    def sync_to_runtime_config():
        """
        Met à jour EN PLACE config.settings.DRENAET_INFO avec les valeurs
        actuelles (BD + défauts). C'est cette synchronisation qui permet
        aux 8 templates de documents (qui font `info = settings.DRENAET_INFO`
        à chaque génération) de voir les nouvelles valeurs sans aucune
        modification de leur code.

        À appeler :
        - au démarrage de l'application (main.py)
        - après chaque SettingsService.update(...)
        """
        from config import settings as app_config

        current = SettingsService.get_all()

        app_config.DRENAET_INFO["nom_officiel"] = current["nom_officiel"]
        app_config.DRENAET_INFO["ministere"] = current["ministere"]
        app_config.DRENAET_INFO["ville"] = current["ville"]
        app_config.DRENAET_INFO["region"] = current["region"]
        app_config.DRENAET_INFO["bp"] = current["bp"]
        app_config.DRENAET_INFO["telephone"] = current["telephone"]
        app_config.DRENAET_INFO["email"] = current["email"]
        app_config.DRENAET_INFO["directeur_regional_nom"] = current["directeur_regional_nom"]
        app_config.DRENAET_INFO["directeur_regional_titre"] = current["directeur_regional_titre"]
        app_config.DRENAET_INFO["directeur_par_procuration"] = (
            str(current["directeur_par_procuration"]).lower() == "true"
        )

    # ====================================================================
    @staticmethod
    def get_quota_conges_annuel() -> int:
        """Récupère le quota de congés annuel configuré (jours ouvrés/an)."""
        try:
            return int(SettingsService.get("quota_conges_annuel", 30))
        except (ValueError, TypeError):
            return 30

    @staticmethod
    def get_logo_path() -> Optional[str]:
        """Récupère le chemin du logo custom, ou None si non défini."""
        path = SettingsService.get("logo_path", "")
        return path if path else None