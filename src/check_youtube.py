#!/usr/bin/env python3
"""Read-only OAuth check. Never uploads media or prints credentials."""
import os
import sys

REQUIRED = ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
RADAR_CHANNEL_ID = "UCP5NhO1fNzw-fSK1-xXz0jw"
# Revalidar sempre antes de qualquer publicação automática.


def verify_channel(yt, expected):
    response = yt.channels().list(part="id,snippet", mine=True).execute()
    channels = response.get("items", [])
    if len(channels) != 1:
        raise RuntimeError("Selecione exatamente um canal durante o consentimento OAuth.")
    channel = channels[0]
    if channel["id"] != expected:
        raise RuntimeError("Canal autorizado diferente do Radar dos Games. Nenhum upload foi feito.")
    return channel["id"]


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
        expected = (os.environ.get("YT_CHANNEL_ID") or RADAR_CHANNEL_ID).strip()
        cid = verify_channel(service(), expected)
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
    print("OAuth VALIDADO: token renovado e canal Radar dos Games confirmado (" + cid + "). Nenhum upload feito.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
