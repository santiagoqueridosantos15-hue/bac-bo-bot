import os
import time
import math
import random
import requests
from datetime import date, timedelta

# ==============================================================================
# 1. CONFIGURAÇÃO SIMPLES (LÊ DO RENDER SE EXISTIR, OU USA O VALOR DIRETO)
# ==============================================================================
# Dica: depois de testar, gera chaves novas e mete em Environment no Render
# para não ficarem expostas no código/GitHub.
TELEGRAM_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN")
    or "8922303337:AAEkDbFYIa9hyz28nMdvq0iuO0oVYotVspE"
).strip()

FOOTBALL_DATA_KEY = (
    os.getenv("FOOTBALL_DATA_KEY")
    or os.getenv("SPORTS_API_KEY")
    or "72a4ea44f89040fb822a5990dbb7c2ef"
).strip()

BASE_URL = "https://api.football-data.org/v4"

CACHE = {}
CACHE_TTL = 1800  # 30 minutos em cache para poupar pedidos
ULTIMO_PEDIDO_TS = 0.0


# ==============================================================================
# 2. LIGAÇÃO À API FOOTBALL-DATA.ORG COM CACHE
# ==============================================================================
def fd_get(endpoint: str, params: dict | None = None):
    global ULTIMO_PEDIDO_TS

    if not FOOTBALL_DATA_KEY or FOOTBALL_DATA_KEY.startswith("COLA_AQUI"):
        raise ValueError("Falta configurar a chave do Football-Data.org.")

    url = f"{BASE_URL}{endpoint}"
    cache_key = (url, tuple(sorted((params or {}).items())))
    agora = time.time()

    if cache_key in CACHE and (agora - CACHE[cache_key]["ts"]) < CACHE_TTL:
        return CACHE[cache_key]["data"]

    delta = agora - ULTIMO_PEDIDO_TS
    if delta < 6.5:
        time.sleep(6.5 - delta)

    headers = {"X-Auth-Token": FOOTBALL_DATA_KEY}
    resp = requests.get(url, headers=headers, params=params, timeout=20)
    ULTIMO_PEDIDO_TS = time.time()
    resp.raise_for_status()

    dados = resp.json()
    CACHE[cache_key] = {"ts": agora, "data": dados}
    return dados


def obter_tabela_classificacao(comp_code: str) -> dict:
    try:
        data = fd_get(f"/competitions/{comp_code}/standings")
    except Exception:
        return {}

    mapa = {}
    for standing in data.get("standings", []):
        if standing.get("type") == "TOTAL":
            for row in standing.get("table", []):
                tid = row.get("team", {}).get("id")
                if tid is not None:
                    played = max(1, row.get("playedGames", 1))
                    mapa[tid] = {
                        "pos": row.get("position", 10),
                        "media_gf": row.get("goalsFor", 0) / played,
                        "media_ga": row.get("goalsAgainst", 0) / played,
                        "home_gf": None,
                        "home_ga": None,
                        "away_gf": None,
                        "away_ga": None,
                    }

    for standing in data.get("standings", []):
        stype = standing.get("type")
        if stype in ("HOME", "AWAY"):
            for row in standing.get("table", []):
                tid = row.get("team", {}).get("id")
                if tid in mapa:
                    played = max(1, row.get("playedGames", 1))
                    if stype == "HOME":
                        mapa[tid]["home_gf"] = row.get("goalsFor", 0) / played
                        mapa[tid]["home_ga"] = row.get("goalsAgainst", 0) / played
                    else:
                        mapa[tid]["away_gf"] = row.get("goalsFor", 0) / played
                        mapa[tid]["away_ga"] = row.get("goalsAgainst", 0) / played
    return mapa


def analisar_historico_equipa(team_id: int, is_home: bool, tabela_info: dict | None):
    try:
        data = fd_get(f"/teams/{team_id}/matches", params={"status": "FINISHED", "limit": 10})
        jogos = data.get("matches", [])
    except Exception:
        jogos = []

    ultimos = jogos[-6:] if jogos else []
    pontos = 0.0
    empates = 0
    over25 = 0
    adversarios_ids = []
    h2h_por_adversario = {}

    for m in ultimos:
        home_id = m.get("homeTeam", {}).get("id")
        away_id = m.get("awayTeam", {}).get("id")
        score = m.get("score", {}).get("fullTime", {})
        hg = score.get("home")
        ag = score.get("away")

        if hg is None or ag is None:
            continue

        total_g = hg + ag
        if total_g >= 3:
            over25 += 1

        if home_id == team_id:
            gf, ga, opp_id = hg, ag, away_id
        else:
            gf, ga, opp_id = ag, hg, home_id

        if opp_id is not None:
            adversarios_ids.append(opp_id)
            h2h_por_adversario.setdefault(opp_id, []).append(total_g)

        if gf > ga:
            pontos += 1.0
        elif gf == ga:
            pontos += 0.35
            empates += 1
        else:
            pontos -= 0.6

    n = max(1, len(ultimos))
    forma_recente = max(-1.0, min(1.0, pontos / n))
    taxa_empate = empates / n
    taxa_over25 = over25 / n

    if tabela_info:
        if is_home:
            gf_epoca = tabela_info["home_gf"] if tabela_info["home_gf"] is not None else tabela_info["media_gf"]
            ga_epoca = tabela_info["home_ga"] if tabela_info["home_ga"] is not None else tabela_info["media_ga"]
        else:
            gf_epoca = tabela_info["away_gf"] if tabela_info["away_gf"] is not None else tabela_info["media_gf"]
            ga_epoca = tabela_info["away_ga"] if tabela_info["away_ga"] is not None else tabela_info["media_ga"]
    else:
        gf_epoca, ga_epoca = 1.3, 1.3

    return {
        "gf_epoca": gf_epoca,
        "ga_epoca": ga_epoca,
        "forma_recente": forma_recente,
        "taxa_empate": taxa_empate,
        "taxa_over25": taxa_over25,
        "adversarios_ids": adversarios_ids,
        "h2h_por_adversario": h2h_por_adversario,
    }


def buscar_jogos_do_dia(dia_iso: str | None = None):
    dia_base = date.fromisoformat(dia_iso) if dia_iso else date.today()
    partidas = []

    for offset_dias in (0, 1, 2):
        alvo = (dia_base + timedelta(days=offset_dias)).isoformat()
        raw = fd_get("/matches", params={"dateFrom": alvo, "dateTo": alvo})
        lista = [
            m for m in raw.get("matches", [])
            if m.get("status") in ("SCHEDULED", "TIMED", "IN_PLAY", "PAUSED")
        ]
        if lista:
            partidas = lista[:8]
            break

    if not partidas:
        return []

    tabelas_cache = {}
    jogos_preparados = []

    for m in partidas:
        comp_code = m.get("competition", {}).get("code")
        liga = m.get("competition", {}).get("name", "Competição")
        home = m.get("homeTeam", {})
        away = m.get("awayTeam", {})
        home_id = home.get("id")
        away_id = away.get("id")

        if not home_id or not away_id:
            continue

        if comp_code and comp_code not in tabelas_cache:
            tabelas_cache[comp_code] = obter_tabela_classificacao(comp_code)
        tabela = tabelas_cache.get(comp_code, {})

        hist_casa = analisar_historico_equipa(home_id, True, tabela.get(home_id))
        hist_fora = analisar_historico_equipa(away_id, False, tabela.get(away_id))

        def forca_adv(adv_ids):
            posicoes = [tabela[oid]["pos"] for oid in adv_ids if oid in tabela]
            if not posicoes:
                return 1.0
            media_pos = sum(posicoes) / len(posicoes)
            return max(0.75, min(1.25, 1.2 - (media_pos - 1) * 0.02))

        h2h_golos = (
            hist_casa["h2h_por_adversario"].get(away_id)
            or hist_fora["h2h_por_adversario"].get(home_id)
        )
        h2h_media_golos = (sum(h2h_golos) / len(h2h_golos)) if h2h_golos else 2.5

        nome_casa = home.get("shortName") or home.get("name", "Casa")
        nome_fora = away.get("shortName") or away.get("name", "Fora")

        jogos_preparados.append({
            "jogo": f"{nome_casa} vs {nome_fora}",
            "liga": liga,
            "golos_marcados_casa": hist_casa["gf_epoca"],
            "golos_sofridos_casa": hist_casa["ga_epoca"],
            "golos_marcados_fora": hist_fora["gf_epoca"],
            "golos_sofridos_fora": hist_fora["ga_epoca"],
            "forma_recente_casa": hist_casa["forma_recente"],
            "forma_recente_fora": hist_fora["forma_recente"],
            "forca_adversarios_casa": forca_adv(hist_casa["adversarios_ids"]),
            "forca_adversarios_fora": forca_adv(hist_fora["adversarios_ids"]),
            "h2h_golos_media": h2h_media_golos,
            "h2h_empate_taxa": 0.28,
            "taxa_empate_equipas": (hist_casa["taxa_empate"] + hist_fora["taxa_empate"]) / 2.0,
            "taxa_over25_equipas": (hist_casa["taxa_over25"] + hist_fora["taxa_over25"]) / 2.0,
        })

    return jogos_preparados


# ==============================================================================
# 3. MOTOR DE AVALIAÇÃO (SEM CONDIÇÃO FÍSICA)
# ==============================================================================
def _poisson_sample(lam: float, rng: random.Random) -> int:
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def avaliar_jogo(j: dict) -> dict | None:
    mult_casa = max(
        0.65,
        min(1.35, 1.0 + 0.15 * j["forma_recente_casa"] + 0.15 * (j["forca_adversarios_casa"] - 1.0)),
    )
    mult_fora = max(
        0.65,
        min(1.35, 1.0 + 0.15 * j["forma_recente_fora"] + 0.15 * (j["forca_adversarios_fora"] - 1.0)),
    )

    lam_casa = max(0.25, ((j["golos_marcados_casa"] + j["golos_sofridos_fora"]) / 2.0) * mult_casa)
    lam_fora = max(0.25, ((j["golos_marcados_fora"] + j["golos_sofridos_casa"]) / 2.0) * mult_fora)

    total_alvo = max(
        0.6,
        0.70 * (lam_casa + lam_fora)
        + 0.15 * j["h2h_golos_media"]
        + 0.15 * (1.8 + 2.2 * j["taxa_over25_equipas"]),
    )
    escala = total_alvo / max(0.4, (lam_casa + lam_fora))
    lam_casa *= escala
    lam_fora *= escala

    rng = random.Random(hash(j["jogo"]) & 0xFFFFFFFF)
    n_sim = 8000
    v_casa = empate = v_fora = over25 = 0

    for _ in range(n_sim):
        gc = _poisson_sample(lam_casa, rng)
        gf = _poisson_sample(lam_fora, rng)
        if gc > gf:
            v_casa += 1
        elif gc == gf:
            empate += 1
        else:
            v_fora += 1
        if (gc + gf) >= 3:
            over25 += 1

    p1 = (v_casa / n_sim) * 0.85 + max(0.0, (1.0 - j["taxa_empate_equipas"]) * 0.15) * 0.5
    p2 = (v_fora / n_sim) * 0.85 + max(0.0, (1.0 - j["taxa_empate_equipas"]) * 0.15) * 0.5
    px = (empate / n_sim) * 0.70 + (0.5 * j["taxa_empate_equipas"] + 0.5 * j["h2h_empate_taxa"]) * 0.30

    soma = p1 + px + p2
    p1, px, p2 = p1 / soma, px / soma, p2 / soma
    p_over = max(0.0, min(1.0, (over25 / n_sim) * 0.80 + j["taxa_over25_equipas"] * 0.20))

    candidatos = [
        ("Vitória Casa (1)", "Resultado Final (1X2)", "Casa (1)", p1),
        ("Empate (X)", "Resultado Final (1X2)", "Empate (X)", px),
        ("Vitória Fora (2)", "Resultado Final (1X2)", "Fora (2)", p2),
        ("Mais de 2,5 golos", "Total de Golos (Over/Under 2.5)", "Mais de 2,5 golos (+2.5)", p_over),
    ]
    nome_aposta, mercado, selecao, prob = max(candidatos, key=lambda c: c[3])

    if prob < 0.48:
        return None

    if prob >= 0.62:
        confianca = f"Alta ({prob*100:.0f}%)"
    elif prob >= 0.54:
        confianca = f"Média ({prob*100:.0f}%)"
    else:
        confianca = f"Moderada ({prob*100:.0f}%)"

    return {
        "jogo": j["jogo"],
        "liga": j["liga"],
        "aposta": nome_aposta,
        "onde_apostar": f"{mercado} -> {selecao}",
        "confianca": confianca,
    }


# ==============================================================================
# 4. BOT TELEGRAM (/start e /análise)
# ==============================================================================
def telegram_api(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def formatar_resposta_analise() -> str:
    jogos = buscar_jogos_do_dia()
    oportunidades = [op for j in jogos if (op := avaliar_jogo(j))]

    if not oportunidades:
        return (
            "🔍 *Análise concluída*\n\n"
            "Não encontrei jogos com vantagem clara nos critérios avaliados."
        )

    linhas = ["📊 *Jogos com oportunidade encontrados:*\n"]
    for idx, op in enumerate(oportunidades, start=1):
        linhas.append(
            f"{idx}. *{op['jogo']}* ({op['liga']})\n"
            f"   • *Aposta:* {op['aposta']}\n"
            f"   • *Confiança:* {op['confianca']}\n"
            f"   • *Onde apostar:* {op['onde_apostar']}\n"
        )
    return "\n".join(linhas)


def rodar_bot():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN.startswith("COLA_AQUI"):
        raise ValueError("Falta configurar o token do Telegram.")

    offset = None
    print("Robô ligado. À espera de /start ou /análise no Telegram...")
    while True:
        params = {"timeout": 30}
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
                        "👋 *Robô ativo!*\n\n"
                        "Envia */análise* (ou */analise*) para ver:\n"
                        "• Jogos com oportunidade\n"
                        "• Aposta recomendada (1, X, 2 ou Mais de 2,5 golos)\n"
                        "• Confiança\n"
                        "• Onde apostar (mercado e seleção)"
                    ),
                    "parse_mode": "Markdown",
                })
            elif texto.startswith("/análise") or texto.startswith("/analise"):
                telegram_api("sendMessage", {
                    "chat_id": chat_id,
                    "text": "⏳ A analisar jogos, época, forma, confrontos diretos e mercados...",
                    "parse_mode": "Markdown",
                })
                try:
                    resposta = formatar_resposta_analise()
                except Exception as e:
                    resposta = f"⚠️ Erro: `{e}`"

                telegram_api("sendMessage", {
                    "chat_id": chat_id,
                    "text": resposta,
                    "parse_mode": "Markdown",
                })


if __name__ == "__main__":
    rodar_bot()
