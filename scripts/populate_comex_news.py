"""Popula a tabela comex_news no Supabase com notícias COMEX."""
import os
from typing import List, Dict

from dotenv import load_dotenv
from supabase import create_client, Client


def load_env() -> None:
    """Carrega variáveis de ambiente do .env, se existir."""
    load_dotenv()


def build_supabase_client() -> Client:
    """Inicializa o cliente Supabase usando URL e SERVICE KEY."""
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not service_key:
        raise RuntimeError("SUPABASE_URL e SUPABASE_SERVICE_KEY são obrigatórios para popular comex_news.")

    return create_client(supabase_url, service_key)


def seed_payload() -> List[Dict[str, str]]:
    """Retorna lista de notícias a serem inseridas."""
    created_at_str = "2025-10-24T20:02:24.471508+00:00"

    return [
        {
            "created_at": created_at_str,
            "source": "FollowUP do Comex (Beehiiv)",
            "title": "RIGOR NA TABELA DO FRETE ACENDE ALERTA",
            "link": "https://followupdocomex.beehiiv.com/p/rigor-na-tabela-do-frete-acende-alerta",
            "summary": "Pressão alemã pelo acordo UE–Mercosul e tarifas dos EUA elevam tensão no setor de proteínas.",
            "publishedAt": "1 hour ago",
        },
        {
            "created_at": created_at_str,
            "source": "CNN Brasil",
            "title": "LULA-TRUMP: GOVERNO TORCE POR PAUSA NO TARIFAÇO",
            "link": "https://www.cnnbrasil.com.br/economia/lula-trump-brasil-torce-por-pausa-no-tarifaco/",
            "summary": "",
            "publishedAt": "24/10/2025 | 10:57",
        },
        {
            "created_at": created_at_str,
            "source": "CNN Brasil",
            "title": "ANÁLISE: TARIFAÇO SERÁ NEGOCIADO POR EQUIPES DO BRASIL E EUA",
            "link": "https://www.cnnbrasil.com.br/economia/analise-tarifaco-sera-negociado-por-equipes-do-brasil-e-eua/",
            "summary": "",
            "publishedAt": "24/10/2025 | 10:54",
        },
        {
            "created_at": created_at_str,
            "source": "CNN Brasil",
            "title": "LULA DIZ QUE ESTÁ ABERTO A DISCUTIR QUALQUER ASSUNTO COM TRUMP",
            "link": "https://www.cnnbrasil.com.br/internacional/lula-diz-que-esta-aberto-a-discutir-qualquer-assunto-com-trump/",
            "summary": "",
            "publishedAt": "24/10/2025 | 10:25",
        },
        {
            "created_at": created_at_str,
            "source": "CNN Brasil",
            "title": "BRASIL ESPERA ENCONTRO LULA-TRUMP COMO QUEBRA-GELO",
            "link": "https://www.cnnbrasil.com.br/internacional/brasil-espera-encontro-lula-trump-como-quebra-gelo/",
            "summary": "",
            "publishedAt": "24/10/2025 | 09:48",
        },
        {
            "created_at": created_at_str,
            "source": "FollowUP do Comex (Beehiiv)",
            "title": "155%: TRUMP PRESSIONA PEQUIM",
            "link": "https://followupdocomex.beehiiv.com/p/155-trump-pressiona-pequim",
            "summary": "Gecex zera alíquotas de importação e Brasil pode liderar produção de biocombustível aéreo.",
            "publishedAt": "19 hours ago",
        },
    ]


def populate() -> None:
    """Insere notícias na tabela comex_news."""
    load_env()
    client = build_supabase_client()
    payload = seed_payload()

    print(f"Inserindo {len(payload)} notícias em comex_news...")
    response = client.table("comex_news").insert(payload).execute()
    inserted = response.data or []

    print(f"✅ Notícias inseridas com sucesso. Registros inseridos: {len(inserted)}")


if __name__ == "__main__":
    populate()
