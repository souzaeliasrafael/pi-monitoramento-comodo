import sys
from pathlib import Path
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import argparse
import json
import logging

from app.config import load_settings
from app.services.demo import setup_demo
from app.logging_config import command_entrypoint


@command_entrypoint
def main():
    parser = argparse.ArgumentParser(description="Prepara demonstração com dados simulados; faz backup e recria tabelas do banco configurado. Pare o coletor antes de executar.")
    parser.add_argument("--days", type=int, default=60, help="Entre 30 e 90; padrão 60")
    parser.add_argument("--records", type=int, help="Total exato de leituras, múltiplo de quatro; ex.: --days 33 --records 5000")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print(json.dumps(setup_demo(load_settings(), args.days, records=args.records), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
