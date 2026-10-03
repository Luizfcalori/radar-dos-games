#!/usr/bin/env python3
"""Read-only OAuth check. Never uploads media or prints credentials."""
import os
import sys

REQUIRED = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
RADAR_CHANNEL_ID = "UCSZJZE-E10SVdx42wrDeWhw"
RADAR_CHANNEL_TITLE = "Radar dos Games"


def verify_channel(yt, expected_id=RADAR_CHANNEL_ID):
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
    if cid != expected_id:
        raise RuntimeError(
            f"ID do canal autorizado diferente do Radar dos Games: {cid}. Esperado: {expected_id}. Nenhum upload foi feito."
        )
    return cid, title


def safe_refresh_reason(error):
    """Return only Google's error code/description; never credentials or request data."""
    code = "refresh_error"
    description = "token recusado pelo Google"
    for arg in getattr(error, "args", ()):
        if isinstance(arg, dict):
            code = str(arg.get("error") or code)
            description = str(arg.get("error_description") or description)
    return f"{code}: {description}"


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
        cid, title = verify_channel(service())
    except RefreshError as error:
        print("OAuth recusado: " + safe_refresh_reason(error) + ". Reautorize o canal.")
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
