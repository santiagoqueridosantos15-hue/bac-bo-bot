import os
import time
import math
import csv
import io
import unicodedata
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ==============================================================================
# 1. CONFIGURAÇÃO (API-FOOTBALL + FOOTBALL-DATA.CO.UK)
# ==============================================================================
TELEGRAM_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or "8922303337:AAFciW_ITq1-RLVUeosPelGQLYkH7MN2tPc"
).strip()

API_FOOTBALL_KEY = (
    os.getenv("API_FOOTBALL_KEY")
    or os.getenv("API_FOOBALL_KEY")
    
).strip()

TZ_LISBOA = ZoneInfo("Europe/Lisbon")
API_FB_BASE = "https://v3.football.api-sports.io"

EPOCA_FD = "2627"
LIGAS_FD = [
    "P1", "E0", "SP1", "I1", "D1", "F1", "N1", "B1", "T1", "E1",
]

CACHE = {}
CACHE_TTL = 1800  # 30 minutos


def _normalizar(nome: str) -> str:
    txt = unicodedata.normalize("NFKD", nome or "")
    txt = "".join(c for c in txt if not unicodedata.combining(c)).lower()
    for lixo in ["fc ", "sc ", "cf ", "ac ", "as ", "sl ", "cd ", "ud ", "rc ", "afc ", "ssc ", "us ", "sv ", "vfb ", "fsv "]:
        if txt.startswith(lixo):
            txt = txt[len(lixo):]
    return " ".join(txt.replace("-", " ").replace(".", " ").split())


# ==============================================================================
# 2. BUSCAR JOGOS REAIS DE HOJE E AMANHÃ (API-FOOTBALL)
# ==============================================================================
def buscar_jogos_reais_dia(data_str: str) -> list[dict]:
    if not API_FOOTBALL_KEY or API_FOOTBALL_KEY.startswith("COLA_AQUI"):
        raise RuntimeError("Falta configurar a API_FOOTBALL_KEY.")

    cache_key = ("fixtures", data_str)
    agora = time.time()
    if cache_key in CACHE and (agora - CACHE[cache_key]["ts"]) < CACHE_TTL:
        return CACHE[cache_key]["data"]

    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    params = {"date": data_str, "timezone": "Europe/Lisbon"}
    resp = requests.get(f"{API_FB_BASE}/fixtures", headers=headers, params=params, timeout=25)
    resp.raise_for_status()
    payload = resp.json() or {}

    if payload.get("errors"):
        raise RuntimeError(f"Erro API-Football: {payload['errors']}")

    jogos = []
    for item in payload.get("response") or []:
        status_short = ((item.get("fixture") or {}).get("status") or {}).get("short") or ""
        if status_short in {"FT", "AET", "PEN", "PST", "CANC", "ABD", "AWD", "WO"}:
            continue

        casa = (((item.get("teams") or {}).get("home") or {}).get("name") or "").strip()
        fora = (((item.get("teams") or {}).get("away") or {}).get("name") or "").strip()
        if not casa or not fora:
            continue

        liga = ((item.get("league") or {}).get("name") or "Futebol").strip()
        data_iso = ((item.get("fixture") or {}).get("date") or "")
        hora_str = data_iso.split("T")[1][:5] if "T" in data_iso else "--:--"

        jogos.append({
            "casa": casa,
            "fora": fora,
            "liga": liga,
            "hora": hora_str,
            "data_jogo": data_str,
        })

    CACHE[cache_key] = {"ts": agora, "data": jogos}
    return jogos


# ==============================================================================
# 3. HISTÓRICO REAL DAS EQUIPAS (FOOTBALL-DATA.CO.UK)
# ==============================================================================
def carregar_estatisticas_fd() -> dict:
    cache_key = ("fd_stats", EPOCA_FD)
    agora = time.time()
    if cache_key in CACHE and (agora - CACHE[cache_key]["ts"]) < CACHE_TTL:
        return CACHE[cache_key]["data"]

    equipas = {}

    def _registo(chave: str):
        if chave not in equipas:
            equipas[chave] = {
                "h_j": 0, "h_gm": 0, "h_gs": 0,
                "a_j": 0, "a_gm": 0, "a_gs": 0,
                "tot_g": 0, "tot_j": 0,
                "ultimos": [],  # (gm, gs, res)
            }
        return equipas[chave]

    for liga_code in LIGAS_FD:
        url = f"https://www.football-data.co.uk/mmz4281/{EPOCA_FD}/{liga_code}.csv"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200:
                continue
            texto = r.content.decode("latin-1", errors="ignore")
            for linha in csv.DictReader(io.StringIO(texto)):
                h_nome = (linha.get("HomeTeam") or "").strip()
                a_nome = (linha.get("AwayTeam") or "").strip()
                if not h_nome or not a_nome:
                    continue
                try:
                    hg = int(float(linha.get("FTHG", "")))
                    ag = int(float(linha.get("FTAG", "")))
                except ValueError:
                    continue

                ftr = (linha.get("FTR") or "").strip()
                eh = _registo(_normalizar(h_nome))
                ea = _registo(_normalizar(a_nome))

                eh["h_j"] += 1
                eh["h_gm"] += hg
                eh["h_gs"] += ag
                eh["tot_j"] += 1
                eh["tot_g"] += hg + ag
                eh["ultimos"].append((hg, ag, "V" if ftr == "H" else "E" if ftr == "D" else "D"))

                ea["a_j"] += 1
                ea["a_gm"] += ag
                ea["a_gs"] += hg
                ea["tot_j"] += 1
                ea["tot_g"] += hg + ag
                ea["ultimos"].append((ag, hg, "V" if ftr == "A" else "E" if ftr == "D" else "D"))
        except Exception:
            continue

    CACHE[cache_key] = {"ts": agora, "data": equipas}
    return equipas


def _encontrar_stats(nome_equipa: str, base_stats: dict) -> dict | None:
    alvo = _normalizar(nome_equipa)
    if alvo in base_stats:
        return base_stats[alvo]
    for chave, dados in base_stats.items():
        if alvo and (alvo in chave or chave in alvo):
            return dados
    return None


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _forma_str(ultimos: list) -> str:
    if not ultimos:
        return "Sem registo"
    return "".join(res for _, _, res in ultimos[-5:])


# ==============================================================================
# 4. ANÁLISE NO ESTILO FOOTBALL AI PRO (1 / 2 / X / +2,5 GOLOS / AMBAS MARCAM)
# ==============================================================================
def analisar_cartao(jogo: dict, base_stats: dict) -> dict:
    st_c = _encontrar_stats(jogo["casa"], base_stats)
    st_f = _encontrar_stats(jogo["fora"], base_stats)

    if not st_c or not st_f or st_c["h_j"] < 2 or st_f["a_j"] < 2:
        return {
            "liga": jogo["liga"],
            "hora": jogo["hora"],
            "titulo": f"{jogo['casa'].upper()} VS {jogo['fora'].upper()}",
            "recomendacao": "DEIXAR PASSAR",
            "prob": "—",
            "confianca": "baixa",
            "mercado": "Sem entrada",
            "resumo": "Sem histórico estatístico suficiente em ambas as equipas para validar entrada com assertividade.",
        }

    h_gm = st_c["h_gm"] / st_c["h_j"]
    h_gs = st_c["h_gs"] / st_c["h_j"]
    a_gm = st_f["a_gm"] / st_f["a_j"]
    a_gs = st_f["a_gs"] / st_f["a_j"]

    ult_c = st_c["ultimos"][-6:]
    ult_f = st_f["ultimos"][-6:]

    pts_c = sum(3 if r == "V" else 1 if r == "E" else 0 for _, _, r in ult_c) / max(1, len(ult_c) * 3)
    pts_f = sum(3 if r == "V" else 1 if r == "E" else 0 for _, _, r in ult_f) / max(1, len(ult_f) * 3)

    btts_c = sum(1 for gm, gs, _ in ult_c if gm >= 1 and gs >= 1) / max(1, len(ult_c))
    btts_f = sum(1 for gm, gs, _ in ult_f if gm >= 1 and gs >= 1) / max(1, len(ult_f))

    lam_c = max(0.25, ((h_gm + a_gs) / 2.0) * (0.85 + 0.30 * pts_c))
    lam_f = max(0.25, ((a_gm + h_gs) / 2.0) * (0.85 + 0.30 * pts_f))
    total_esp = lam_c + lam_f

    media_ritmo = ((st_c["tot_g"] / max(1, st_c["tot_j"])) + (st_f["tot_g"] / max(1, st_f["tot_j"]))) / 2.0

    p1 = px = p2 = p_over25 = p_btts = 0.0
    for gc in range(8):
        pc = _poisson_pmf(gc, lam_c)
        for gf in range(8):
            p = pc * _poisson_pmf(gf, lam_f)
            if gc > gf:
                p1 += p
            elif gc == gf:
                px += p
            else:
                p2 += p
            if (gc + gf) >= 3:
                p_over25 += p
            if gc >= 1 and gf >= 1:
                p_btts += p

    p_btts = max(0.0, min(1.0, 0.75 * p_btts + 0.25 * ((btts_c + btts_f) / 2.0)))

    # Apenas mercados permitidos: Ganhar (1 ou 2), Empate (X), Mais de 2,5 golos, Ambas marcam
    escolhas = [
        ("VITÓRIA DA CASA", "Resultado (1)", p1),
        ("VITÓRIA FORA", "Resultado (2)", p2),
        ("EMPATE", "Resultado (X)", px),
        ("MAIS DE 2,5 GOLOS", "Golos (+2,5)", p_over25),
        ("AMBAS MARCAM — SIM", "BTTS (Sim)", p_btts),
    ]
    rec, mercado, prob_val = max(escolhas, key=lambda x: x[2])

    if prob_val < 0.45:
        rec = "DEIXAR PASSAR"
        mercado = "Sem vantagem"

    prob_pct = f"{prob_val * 100:.1f}%".replace(".", ",")
    conf = "alta" if prob_val >= 0.58 else ("média" if prob_val >= 0.46 else "baixa")

    forma_c = _forma_str(st_c["ultimos"])
    forma_f = _forma_str(st_f["ultimos"])

    resumo = (
        f"Golos esperados {lam_c:.1f}–{lam_f:.1f} (total {total_esp:.1f}; média {media_ritmo:.1f}). "
        f"{jogo['casa']} marca {h_gm:.1f} e sofre {h_gs:.1f} em casa (forma {forma_c}); "
        f"{jogo['fora']} marca {a_gm:.1f} e sofre {a_gs:.1f} fora (forma {forma_f})."
    ).replace(".", ",")

    return {
        "liga": jogo["liga"],
        "hora": jogo["hora"],
        "titulo": f"{jogo['casa'].upper()} VS {jogo['fora'].upper()}",
        "recomendacao": rec,
        "prob": prob_pct,
        "confianca": conf,
        "mercado": mercado,
        "resumo": resumo,
    }


# ==============================================================================
# 5. BOT TELEGRAM (/start e /análise)
# ==============================================================================
def telegram_api(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    r = requests.post(url, json=payload, timeout=45)
    r.raise_for_status()
    return r.json()


def _formatar_cartao(c: dict) -> str:
    return (
        f"*{c['liga']} · {c['hora']}*\n"
        f"*{c['titulo']}*\n"
        f"RECOMENDAÇÃO DA IA\n"
        f"*{c['recomendacao']}*\n\n"
        f"PROBABILIDADE: *{c['prob']}*  |  CONFIANÇA: *{c['confianca']}*  |  MERCADO: *{c['mercado']}*\n"
        f"_{c['resumo']}_\n"
    )


def formatar_resposta() -> str:
    hoje_dt = datetime.now(TZ_LISBOA).date()
    amanha_dt = hoje_dt + timedelta(days=1)
    base_stats = carregar_estatisticas_fd()

    partes = ["*FOOTBALL AI PRO — HOJE E AMANHÃ*\n"]

    for rotulo, dt in [("HOJE", hoje_dt), ("AMANHÃ", amanha_dt)]:
        partes.append(f"📅 *{rotulo} ({dt.isoformat()})*\n")
        jogos = buscar_jogos_reais_dia(dt.isoformat())[:5]
        if not jogos:
            partes.append("• Sem jogos reais agendados encontrados nesta data.\n")
        else:
            for j in jogos:
                partes.append(_formatar_cartao(analisar_cartao(j, base_stats)))
                partes.append("────────────────────\n")

    return "\n".join(partes)


def rodar_bot():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN.startswith("COLA_AQUI"):
        raise ValueError("Falta configurar o TELEGRAM_TOKEN.")

    offset = None
    print("Robô ativo no estilo Football AI Pro...")
    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset

            updates = telegram_api("getUpdates", params).get("result", [])
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message") or {}
                chat_id = msg.get("chat", {}).get("id")
                texto = (msg.get("text") or "").strip().lower()

                if not chat_id or not texto:
                    continue

                if texto.startswith("/start"):
                    telegram_api("sendMessage", {
                        "chat_id": chat_id,
                        "text": (
                            "👋 *FOOTBALL AI PRO — TELEGRAM*\n\n"
                            "Envia */análise* (ou */analise*) para ver os jogos reais de *hoje e amanhã* "
                            "com probabilidade, confiança e leitura estatística."
                        ),
                        "parse_mode": "Markdown",
                    })
                elif texto.startswith("/análise") or texto.startswith("/analise"):
                    telegram_api("sendMessage", {
                        "chat_id": chat_id,
                        "text": "⏳ A carregar jogos reais de hoje e amanhã...",
                        "parse_mode": "Markdown",
                    })
                    try:
                        msg_texto = formatar_resposta()
                    except Exception as e:
                        msg_texto = f"⚠️ Erro: `{e}`"

                    telegram_api("sendMessage", {
                        "chat_id": chat_id,
                        "text": msg_texto,
                        "parse_mode": "Markdown",
                    })
        except Exception as e:
            print(f"Aviso de ligação: {e}")
            time.sleep(5)


if __name__ == "__main__":
    rodar_bot()
