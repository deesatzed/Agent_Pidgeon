from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_pidgin.catalog import SeedCatalog
from agent_pidgin.config import PidginConfig
from agent_pidgin.mount_gateway import LocalMountGateway
from agent_pidgin.policy import load_policy
from agent_pidgin.service import PidginReceiverService


def resolve_sample_contract() -> dict[str, Any]:
    demo_dir = Path(__file__).resolve().parent
    contract = json.loads((demo_dir / "sample_contract.json").read_text(encoding="utf-8"))
    config = PidginConfig.from_env()
    service = PidginReceiverService(
        mount_gateway=LocalMountGateway(),
        catalog=SeedCatalog.load_default(),
        default_mount_root=config.mount_root,
    )
    return service.resolve_message(contract, config=config, policy=load_policy())


def main() -> None:
    print(json.dumps(resolve_sample_contract(), indent=2))


if __name__ == "__main__":
    main()
