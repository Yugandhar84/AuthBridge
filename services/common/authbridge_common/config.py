"""Environment-driven settings shared by both services.

Each service reads its own prefixed variables first (PAYER_SNOWFLAKE_USER,
PROVIDER_SNOWFLAKE_USER, ...) and falls back to the unprefixed name, so one
.env file can configure two service users with different roles.
"""

import os
from dataclasses import dataclass
from pathlib import Path


def _env(prefix, name, default=None):
    return os.getenv("%s_%s" % (prefix, name)) or os.getenv(name) or default


@dataclass
class Settings:
    service: str
    backend: str                 # mock | snowflake
    ai: str                      # mock | cortex
    seed_dir: Path
    sf_account: str = None
    sf_user: str = None
    sf_role: str = None
    sf_warehouse: str = None
    sf_database: str = "AUTHBRIDGE"
    sf_private_key_path: str = None
    sf_private_key_passphrase: str = None
    sf_pat: str = None
    sf_host: str = None
    llm_model: str = None
    validator_mode: str = "structural"   # structural | cli
    validator_jar: str = None

    @property
    def use_snowflake(self):
        return self.backend == "snowflake"

    @property
    def use_cortex(self):
        return self.ai == "cortex"


def _default_seed_dir():
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "shared" / "seed"
        if candidate.is_dir():
            return candidate
    return Path("/app/shared/seed")


def load_settings(service):
    p = service.upper()
    s = Settings(
        service=service,
        backend=_env(p, "AUTHBRIDGE_BACKEND", "mock").lower(),
        ai=_env(p, "AUTHBRIDGE_AI", "mock").lower(),
        seed_dir=Path(_env(p, "AUTHBRIDGE_SEED_DIR") or _default_seed_dir()),
        sf_account=_env(p, "SNOWFLAKE_ACCOUNT"),
        sf_user=_env(p, "SNOWFLAKE_USER"),
        sf_role=_env(p, "SNOWFLAKE_ROLE"),
        sf_warehouse=_env(p, "SNOWFLAKE_WAREHOUSE", "AUTHBRIDGE_APP_WH"),
        sf_database=_env(p, "SNOWFLAKE_DATABASE", "AUTHBRIDGE"),
        sf_private_key_path=_env(p, "SNOWFLAKE_PRIVATE_KEY_PATH"),
        sf_private_key_passphrase=_env(p, "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"),
        sf_pat=_env(p, "SNOWFLAKE_PAT"),
        sf_host=_env(p, "SNOWFLAKE_HOST"),
        llm_model=_env(p, "AUTHBRIDGE_LLM_MODEL"),
        validator_mode=_env(p, "FHIR_VALIDATOR_MODE", "structural").lower(),
        validator_jar=_env(p, "FHIR_VALIDATOR_JAR"),
    )
    if s.use_cortex and not s.use_snowflake:
        raise RuntimeError("AUTHBRIDGE_AI=cortex needs AUTHBRIDGE_BACKEND=snowflake")
    return s
