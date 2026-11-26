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
    or "e8086f77-5ea5-446b-9b6e-d08aa68fa061"
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
# 3. HISTÓRICO REAL, ELO CONTÍNUO, DECAIMENTO TEMPORAL E MÉDIAS DE LIGA
# ==============================================================================
def _parse_data_ddmmyyyy(d_str: str) -> datetime | None:
    d_str = (d_str or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(d_str, fmt)
        except ValueError:
            continue
    return None


def carregar_base_estatistica() -> dict:
    cache_key = ("base_est", EPOCA_FD)
    agora = time.time()
    if cache_key in CACHE and (agora - CACHE[cache_key]["ts"]) < CACHE_TTL:
        return CACHE[cache_key]["data"]

    equipas = {}
    elo = {}
    ligas_hist = {}

    def _reg_equipa(k: str):
        if k not in equipas:
            equipas[k] = {
                "h_jogos": 0, "h_gm_pes": 0.0, "h_gs_pes": 0.0, "h_w_pes": 0.0,
                "a_jogos": 0, "a_gm_pes": 0.0, "a_gs_pes": 0.0, "a_w_pes": 0.0,
                "tot_jogos": 0,
                "ultimos": [],  # (gm, gs, pts_0_a_1)
            }
        return equipas[k]

    def _reg_liga(liga_nome: str):
        if liga_nome not in ligas_hist:
            ligas_hist[liga_nome] = {
                "n": 0, "h_gm": 0.0, "h_gs": 0.0, "a_gm": 0.0, "a_gs": 0.0,
                "p1": 0, "px": 0, "p2": 0, "over25": 0, "btts": 0,
            }
        return ligas_hist[liga_nome]

    hoje_ref = datetime.now()

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
                dt_jogo = _parse_data_ddmmyyyy(linha.get("Date") or "")
                dias_atras = max(0, (hoje_ref - dt_jogo).days) if dt_jogo else 30
                # Decaimento temporal: jogos mais recentes pesam mais
                peso = math.exp(-dias_atras / 75.0)

                kh = _normalizar(h_nome)
                ka = _normalizar(a_nome)
                eh = _reg_equipa(kh)
                ea = _reg_equipa(ka)

                elo_h = elo.get(kh, 1500.0)
                elo_a = elo.get(ka, 1500.0)
                # Bónus de fator casa (+60 pontos Elo)
                esp_h = 1.0 / (1.0 + 10.0 ** (((elo_a) - (elo_h + 60.0)) / 400.0))
                res_h = 1.0 if ftr == "H" else (0.5 if ftr == "D" else 0.0)
                k_elo = 24.0
                elo[kh] = elo_h + k_elo * (res_h - esp_h)
                elo[ka] = elo_a + k_elo * ((1.0 - res_h) - (1.0 - esp_h))

                eh["h_jogos"] += 1
                eh["h_gm_pes"] += hg * peso
                eh["h_gs_pes"] += ag * peso
                eh["h_w_pes"] += peso
                eh["tot_jogos"] += 1
                eh["ultimos"].append((hg, ag, res_h))

                ea["a_jogos"] += 1
                ea["a_gm_pes"] += ag * peso
                ea["a_gs_pes"] += hg * peso
                ea["a_w_pes"] += peso
                ea["tot_jogos"] += 1
                ea["ultimos"].append((ag, hg, 1.0 - res_h))

                rl = _reg_liga(liga_code)
                rl["n"] += 1
                rl["h_gm"] += hg
                rl["h_gs"] += ag
                rl["a_gm"] += ag
                rl["a_gs"] += hg
                if ftr == "H":
                    rl["p1"] += 1
                elif ftr == "D":
                    rl["px"] += 1
                elif ftr == "A":
                    rl["p2"] += 1
                if (hg + ag) >= 3:
                    rl["over25"] += 1
                if hg >= 1 and ag >= 1:
                    rl["btts"] += 1
        except Exception:
            continue

    medias_liga = {}
    for code, rl in ligas_hist.items():
        n = max(1, rl["n"])
        medias_liga[code] = {
            "h_gm": rl["h_gm"] / n,
            "h_gs": rl["h_gs"] / n,
            "a_gm": rl["a_gm"] / n,
            "a_gs": rl["a_gs"] / n,
            "p1": rl["p1"] / n,
            "px": rl["px"] / n,
            "p2": rl["p2"] / n,
            "over25": rl["over25"] / n,
            "btts": rl["btts"] / n,
        }

    global_liga = {
        "h_gm": sum(v["h_gm"] for v in medias_liga.values()) / max(1, len(medias_liga)),
        "h_gs": sum(v["h_gs"] for v in medias_liga.values()) / max(1, len(medias_liga)),
        "a_gm": sum(v["a_gm"] for v in medias_liga.values()) / max(1, len(medias_liga)),
        "a_gs": sum(v["a_gs"] for v in medias_liga.values()) / max(1, len(medias_liga)),
        "p1": sum(v["p1"] for v in medias_liga.values()) / max(1, len(medias_liga)),
        "px": sum(v["px"] for v in medias_liga.values()) / max(1, len(medias_liga)),
        "p2": sum(v["p2"] for v in medias_liga.values()) / max(1, len(medias_liga)),
        "over25": sum(v["over25"] for v in medias_liga.values()) / max(1, len(medias_liga)),
        "btts": sum(v["btts"] for v in medias_liga.values()) / max(1, len(medias_liga)),
    }

    dados = {
        "equipas": equipas,
        "elo": elo,
        "medias_liga": medias_liga,
        "global_liga": global_liga,
    }
    CACHE[cache_key] = {"ts": agora, "data": dados}
    return dados


def _encontrar_chave_e_stats(nome_equipa: str, equipas: dict) -> tuple[str | None, dict | None]:
    alvo = _normalizar(nome_equipa)
    if alvo in equipas:
        return alvo, equipas[alvo]
    for chave, dados in equipas.items():
        if alvo and (alvo in chave or chave in alvo):
            return chave, dados
    return None, None


def _poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def _dixon_coles_tau(gc: int, gf: int, lam_c: float, lam_f: float, rho: float = -0.08) -> float:
    if gc == 0 and gf == 0:
        return max(0.05, 1.0 - lam_c * lam_f * rho)
    if gc == 0 and gf == 1:
        return max(0.05, 1.0 + lam_c * rho)
    if gc == 1 and gf == 0:
        return max(0.05, 1.0 + lam_f * rho)
    if gc == 1 and gf == 1:
        return max(0.05, 1.0 - rho)
    return 1.0


def _momentum_ajuste(ultimos: list) -> float:
    # Últimos 5 jogos ajustam ataque/defesa até ±10%
    ult5 = ultimos[-5:]
    if not ult5:
        return 0.0
    media_pts = sum(p for _, _, p in ult5) / len(ult5)
    # 0.5 é neutro; 1.0 -> +10%; 0.0 -> -10%
    bruto = (media_pts - 0.5) * 0.20
    return max(-0.10, min(0.10, bruto))


# ==============================================================================
# 4. MOTOR COMPLETO (FORÇA + ELO + MOMENTUM + DIXON-COLES + EDGE + EV)
# ==============================================================================
def analisar_jogo_completo(jogo: dict, base: dict, odd_mercado: float | None = None) -> dict:
    equipas = base["equipas"]
    elo_map = base["elo"]
    m_liga = base["global_liga"]

    kc, st_c = _encontrar_chave_e_stats(jogo["casa"], equipas)
    kf, st_f = _encontrar_chave_e_stats(jogo["fora"], equipas)

    if not st_c or not st_f or st_c["tot_jogos"] < 2 or st_f["tot_jogos"] < 2:
        return {
            "casa_norm": kc or _normalizar(jogo["casa"]),
            "fora_norm": kf or _normalizar(jogo["fora"]),
            "liga": jogo["liga"],
            "hora": jogo["hora"],
            "titulo": f"{jogo['casa'].upper()} VS {jogo['fora'].upper()}",
            "recomendacao": "DEIXAR PASSAR",
            "prob_num": 0.0,
            "prob_str": "—",
            "confianca": "baixa",
            "mercado": "Sem dados",
            "resumo": "Histórico insuficiente nas bases carregadas para calcular margem fiável.",
        }

    n_c = st_c["tot_jogos"]
    n_f = st_f["tot_jogos"]
    n_min = min(n_c, n_f)

    # 1. Força Casa vs Fora ajustada às médias da liga
    h_gm = (st_c["h_gm_pes"] / max(1e-6, st_c["h_w_pes"])) if st_c["h_jogos"] > 0 else m_liga["h_gm"]
    h_gs = (st_c["h_gs_pes"] / max(1e-6, st_c["h_w_pes"])) if st_c["h_jogos"] > 0 else m_liga["h_gs"]
    a_gm = (st_f["a_gm_pes"] / max(1e-6, st_f["a_w_pes"])) if st_f["a_jogos"] > 0 else m_liga["a_gm"]
    a_gs = (st_f["a_gs_pes"] / max(1e-6, st_f["a_w_pes"])) if st_f["a_jogos"] > 0 else m_liga["a_gs"]

    forca_atq_c = h_gm / max(0.4, m_liga["h_gm"])
    forca_def_f = a_gs / max(0.4, m_liga["a_gs"])
    forca_atq_f = a_gm / max(0.4, m_liga["a_gm"])
    forca_def_c = h_gs / max(0.4, m_liga["h_gs"])

    # Momentum dos últimos 5 jogos (±10%)
    mom_c = _momentum_ajuste(st_c["ultimos"])
    mom_f = _momentum_ajuste(st_f["ultimos"])

    lam_c = max(0.25, m_liga["h_gm"] * forca_atq_c * forca_def_f * (1.0 + mom_c))
    lam_f = max(0.25, m_liga["a_gm"] * forca_atq_f * forca_def_c * (1.0 + mom_f))

    # 2. Simulação Poisson + correção Dixon-Coles
    p_mat = {}
    soma_p = 0.0
    for gc in range(7):
        pc = _poisson_pmf(gc, lam_c)
        for gf in range(7):
            tau = _dixon_coles_tau(gc, gf, lam_c, lam_f)
            val = pc * _poisson_pmf(gf, lam_f) * tau
            p_mat[(gc, gf)] = val
            soma_p += val
    for k in p_mat:
        p_mat[k] /= max(1e-9, soma_p)

    p1_pois = p2_pois = px_pois = p_over25 = p_btts = 0.0
    for (gc, gf), val in p_mat.items():
        if gc > gf:
            p1_pois += val
        elif gc == gf:
            px_pois += val
        else:
            p2_pois += val
        if (gc + gf) >= 3:
            p_over25 += val
        if gc >= 1 and gf >= 1:
            p_btts += val

    # 3. Elo contínuo (+60 casa) e combinação 70% Poisson + 30% Elo em 1X2
    elo_c = elo_map.get(kc, 1500.0) + 60.0
    elo_f = elo_map.get(kf, 1500.0)
    diff_elo = (elo_c - elo_f) / 400.0
    p1_elo = 1.0 / (1.0 + 10.0 ** (-diff_elo))
    p2_elo = 1.0 - p1_elo
    px_elo = max(0.14, 0.28 * math.exp(-(diff_elo ** 2) * 2.0))
    tot_elo = p1_elo + px_elo + p2_elo
    p1_elo, px_elo, p2_elo = p1_elo / tot_elo, px_elo / tot_elo, p2_elo / tot_elo

    p1 = 0.70 * p1_pois + 0.30 * p1_elo
    px = 0.70 * px_pois + 0.30 * px_elo
    p2 = 0.70 * p2_pois + 0.30 * p2_elo

    # 4. Penalização por incerteza (poucos jogos) e escolha por Edge sobre a liga
    # Se n_min < 20, aplica penalidade proporcional para não inflacionar jogos curtos
    penalidade_incerteza = max(0.0, (20 - n_min) * 0.0035)

    candidatos = [
        ("VITÓRIA DA CASA", "Resultado (1)", p1, m_liga["p1"]),
        ("EMPATE", "Resultado (X)", px, m_liga["px"]),
        ("VITÓRIA FORA", "Resultado (2)", p2, m_liga["p2"]),
        ("MAIS DE 2,5 GOLOS", "Golos (+2,5)", p_over25, m_liga["over25"]),
        ("AMBAS MARCAM — SIM", "BTTS (Sim)", p_btts, m_liga["btts"]),
    ]

    melhor_item = None
    melhor_score = -999.0

    for rec_nome, merc_nome, p_bruta, base_liga_p in candidatos:
        p_aj = max(0.01, min(0.95, p_bruta - penalidade_incerteza))
        odd_justa = 1.0 / max(0.05, p_aj)
        # Exclui linhas triviais com odd justa < 1.25
        if odd_justa < 1.25:
            continue
        edge = p_aj - base_liga_p
        # Exige vantagem sobre a liga; se o edge for muito fraco, penaliza o score
        score = edge + (0.15 * p_aj)
        if score > melhor_score:
            melhor_score = score
            melhor_item = (rec_nome, merc_nome, p_aj, edge, odd_justa)

    if not melhor_item:
        return {
            "casa_norm": kc,
            "fora_norm": kf,
            "liga": jogo["liga"],
            "hora": jogo["hora"],
            "titulo": f"{jogo['casa'].upper()} VS {jogo['fora'].upper()}",
            "recomendacao": "DEIXAR PASSAR",
            "prob_num": 0.0,
            "prob_str": "—",
            "confianca": "baixa",
            "mercado": "Sem Edge",
            "resumo": "Linhas sem vantagem estatística clara face à média da liga.",
        }

    rec_nome, merc_nome, p_final, edge, odd_justa = melhor_item
    conf = "alta" if (n_min >= 20 and p_final >= 0.65) else ("média" if p_final >= 0.45 else "baixa")

    # 5. Regra de EV e Alerta de Ratoeira (se odd for passada, ou estimativa de mercado)
    if odd_mercado and odd_mercado > 1.0:
        ev = (p_final * odd_mercado) - 1.0
        if p_final > 0.65 and ev < 0:
            rec_nome = "DEIXAR PASSAR (RATOEIRA)"
            conf = "baixa"
        elif ev < 0:
            rec_nome = "DEIXAR PASSAR"
            conf = "baixa"
        extra_ev = f" EV: {ev*100:+.1f}% (odd {odd_mercado:.2f})."
    else:
        # Sem odd externa: se edge for negativo (< -0.02), não força entrada
        if edge < -0.02 and p_final < 0.52:
            rec_nome = "DEIXAR PASSAR"
            conf = "baixa"
        extra_ev = f" Edge liga: {edge*100:+.1f}% | Odd justa: {odd_justa:.2f}."

    resumo = (
        f"xG {lam_c:.1f}–{lam_f:.1f} (total {lam_c + lam_f:.1f}). "
        f"Elo {elo_c:.0f} vs {elo_f:.0f}. "
        f"Jogos base: {n_c}/{n_f}.{extra_ev}"
    ).replace(".", ",")

    return {
        "casa_norm": kc,
        "fora_norm": kf,
        "liga": jogo["liga"],
        "hora": jogo["hora"],
        "titulo": f"{jogo['casa'].upper()} VS {jogo['fora'].upper()}",
        "recomendacao": rec_nome,
        "prob_num": p_final,
        "prob_str": f"{p_final * 100:.1f}%".replace(".", ","),
        "confianca": conf,
        "mercado": merc_nome,
        "resumo": resumo,
    }


# ==============================================================================
# 5. MÚLTIPLAS (CONFIANÇA ALTA, >= 20 JOGOS, PROB >= 65%, SEM REPETIR EQUIPAS)
# ==============================================================================
def montar_multiplas(cartoes: list[dict]) -> list[str]:
    elegiveis = [
        c for c in cartoes
        if c["confianca"] == "alta"
        and c["prob_num"] >= 0.65
        and "DEIXAR PASSAR" not in c["recomendacao"]
    ]
    elegiveis.sort(key=lambda x: x["prob_num"], reverse=True)

    boletim = []
    equipas_usadas = set()
    for c in elegiveis:
        if c["casa_norm"] in equipas_usadas or c["fora_norm"] in equipas_usadas:
            continue
        boletim.append(c)
        equipas_usadas.add(c["casa_norm"])
        equipas_usadas.add(c["fora_norm"])
        if len(boletim) == 3:
            break

    if len(boletim) < 2:
        return ["• Sem jogos suficientes com confiança alta (≥20 jogos) e prob. ≥65% sem repetir equipas.\n"]

    tipo = "TRIPLA" if len(boletim) == 3 else "DUPLA"
    linhas = [f"🎯 *{tipo} SELECIONADA*\n"]
    for idx, b in enumerate(boletim, start=1):
        linhas.append(f"{idx}. *{b['titulo']}* → *{b['recomendacao']}* ({b['prob_str']})\n")
    return linhas


# ==============================================================================
# 6. BOT TELEGRAM (/start e /análise)
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
        f"PROBABILIDADE: *{c['prob_str']}*  |  CONFIANÇA: *{c['confianca']}*  |  MERCADO: *{c['mercado']}*\n"
        f"_{c['resumo']}_\n"
    )


def formatar_resposta() -> str:
    hoje_dt = datetime.now(TZ_LISBOA).date()
    amanha_dt = hoje_dt + timedelta(days=1)
    base = carregar_base_estatistica()

    partes = ["*FOOTBALL AI PRO — HOJE E AMANHÃ*\n"]
    todos_cartoes = []

    for rotulo, dt in [("HOJE", hoje_dt), ("AMANHÃ", amanha_dt)]:
        partes.append(f"📅 *{rotulo} ({dt.isoformat()})*\n")
        jogos = buscar_jogos_reais_dia(dt.isoformat())[:6]
        if not jogos:
            partes.append("• Sem jogos reais agendados encontrados nesta data.\n")
        else:
            for j in jogos:
                c = analisar_jogo_completo(j, base)
                todos_cartoes.append(c)
                partes.append(_formatar_cartao(c))
                partes.append("────────────────────\n")

    partes.append("🎲 *MÚLTIPLAS (DUPLAS / TRIPLAS)*\n")
    partes.extend(montar_multiplas(todos_cartoes))

    return "\n".join(partes)


def rodar_bot():
    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN.startswith("COLA_AQUI"):
        raise ValueError("Falta configurar o TELEGRAM_TOKEN.")

    offset = None
    print("Robô ativo com modelo completo (Elo + Dixon-Coles + Edge + Múltiplas)...")
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
                            "com o motor completo e secção de *múltiplas*."
                        ),
                        "parse_mode": "Markdown",
                    })
                elif texto.startswith("/análise") or texto.startswith("/analise"):
                    telegram_api("sendMessage", {
                        "chat_id": chat_id,
                        "text": "⏳ A calcular força, Elo, Dixon-Coles e Edge nos jogos de hoje e amanhã...",
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
