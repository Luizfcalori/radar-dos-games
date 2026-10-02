#!/usr/bin/env python3
"""Read-only OAuth check. Never uploads media or prints credentials."""
import os
import sys

REQUIRED = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
RADAR_CHANNEL_TITLE = "Radar dos Games"


def verify_channel(yt, expected_id=""):
    response = yt.channels().list(part="id,snippet", mine=True).execute()
    channels = response.get("items", [])
    if len(channels) != 1:
        raise RuntimeError("Selecione exatamente um canal durante o consentimento OAuth.")
    channel = channels[0]
    cid = channel["id"]
    title = channel.get("snippet", {}).get("title", "")
    if title.strip().casefold() != RADAR_CHANNEL_TITLE.casefold():
        raise RuntimeError(
            f"Canal autorizado diferente do Radar dos Games: {title} ({cid}). Nenhum upload foi feito."
        )
    if expected_id and cid != expected_id:
        raise RuntimeError(
            f"ID do canal autorizado diferente do Radar dos Games esperado. Nenhum upload foi feito."
        )
    return cid, title


def main():
    missing = [name for name in REQUIRED if not os.environ.get(name, "").strip()]
    if missing:
        print("OAuth PENDENTE. Secrets ausentes: " + ", ".join(missing))
        return 1
    try:
        from google.auth.exceptions import RefreshError
        from googleapiclient.errors import HttpError
        from youtube import service
    except ImportError:
        print("Dependências ausentes. Instale requirements.txt.")
        return 1
    try:
        expected_id = os.environ.get("YT_CHANNEL_ID", "").strip()
        cid, title = verify_channel(service(), expected_id)
    except RefreshError:
        print("OAuth recusado: token expirado/revogado ou cliente incompatível. Reautorize o canal.")
        return 1
    except HttpError as error:
        print(f"YouTube API recusou a consulta (HTTP {error.resp.status}). Verifique API habilitada, escopos e quota.")
        return 1
    except RuntimeError as error:
        print(str(error))
        return 1
    except Exception:
        print("Falha de conexão OAuth/YouTube. Nenhum upload foi feito; tente a validação novamente.")
        return 1
    print(f"OAuth VALIDADO: canal {title} confirmado ({cid}). Nenhum upload feito.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
