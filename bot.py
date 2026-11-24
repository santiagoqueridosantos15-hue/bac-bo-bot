import os
import re
from math import sqrt
from threading import Thread

import telebot
from flask import Flask

# =====================================================
# TWO COLUMNS (NO T PROTECTION) - ADAPTIVE LEARNING BRAIN
# Motor de 2 Colunas (C1+C2 / C1+C3) sem Proteção no T, Martingale até G2 e Aprendizagem Pós-Loss
# =====================================================

TOKEN = os.getenv(
    "BOT_TOKEN",
    "8922303337:AAEfiGQK15Cd4B4SsW-FS97Fq6QyPH2aUEs"
)

if not TOKEN or TOKEN == "COLOCA_AQUI_O_TEU_TOKEN_NOVO":
    raise ValueError("Configura o teu token do Telegram através da variável BOT_TOKEN.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# CONFIGURAÇÕES DE GESTÃO DE BANCA E RISCO (2 COLUNAS, SEM PROTEÇÃO NO T)
ENTRADA_COLUNA = 4      # Aposta base em cada uma das 2 colunas (Entrada)
GALE1_COLUNA = 8        # Aposta em cada uma das 2 colunas no Gale 1 (G1)
GALE2_COLUNA = 16       # Aposta em cada uma das 2 colunas no Gale 2 (G2)

JANELA = 10             # Jogadas iniciais para arrancar
LIMITE_LOSSES = 2       # Máximo de ciclos perdidos (Entrada + G1 + G2 falhados)

MIN_PAPER = 0           # Sem filtro experimental prévio: entra logo em real
MIN_RECENTES = 10       # Janela recente para consulta de estatísticas

# Sessões em memória por chat
sessions = {}


# =====================================================
# SERVIDOR WEB (RENDER 24/7)
# =====================================================

@app.route("/")
def home():
    return "TWO COLUMNS BRAIN - ONLINE 24/7, ZÉ!"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False
    )


# =====================================================
# NOVA SESSÃO
# =====================================================

def nova_sessao():
    return {
        "history": [],          # Lista de resultados ("C1", "C2", "C3", "T", "Z")
        "awaiting_seed": True,

        "active_cols": None,    # Tuplo de 2 colunas, ex: ("C1", "C2") ou ("C1", "C3")
        "active_reason": "",
        "active_strategy": "",
        "gale": 0,              # 0 = Entrada, 1 = Gale 1, 2 = Gale 2
        "blocked": False,

        # Sistema de aprendizagem / autópsia pós-loss
        "error_memory": [],
        "strategy_penalty": {
            "quebra_coluna": 0,
            "alternancia_colunas": 0,
            "atraso_coluna": 0
        },
        "cooldown_by_col": {
            "C1": 0,
            "C2": 0,
            "C3": 0
        },

        # Registo de ciclos concluídos
        "pending_paper": None,
        "pending_paper_g1": None,
        "pending_paper_g2": None,

        # Resultados globais registados
        "paper_results": [],
        "paper_t": 0,

        # Estatísticas individuais por estratégia
        "strategy_stats": {
            "quebra_coluna": {"wins": 0, "losses": 0, "signals": 0},
            "alternancia_colunas": {"wins": 0, "losses": 0, "signals": 0},
            "atraso_coluna": {"wins": 0, "losses": 0, "signals": 0}
        },

        # Estatísticas gerais das operações reais
        "stats": {
            "wins": 0,
            "wins_g1": 0,
            "wins_g2": 0,
            "losses": 0,
            "t_hits": 0,
            "entries": 0,
            "observations": 0
        }
    }


# =====================================================
# CONVERSÃO DE RESULTADO PARA COLUNA / Z
# =====================================================

C1_NUMS = {1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34}
C2_NUMS = {2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35}
C3_NUMS = {3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36}


def parse_token_to_outcome(token):
    t = token.strip().upper()
    if t in ("C1", "1", "1A", "COL1"):
        return "C1"
    if t in ("C2", "2", "2A", "COL2"):
        return "C2"
    if t in ("C3", "3", "3A", "COL3"):
        return "C3"
    if t in ("T", "EMPATE", "TIE"):
        return "T"
    if t in ("Z", "0", "ZERO"):
        return "Z"

    if t.isdigit():
        n = int(t)
        if n == 0:
            return "Z"
        if n in C1_NUMS:
            return "C1"
        if n in C2_NUMS:
            return "C2"
        if n in C3_NUMS:
            return "C3"
    return None


def format_col_nome(col):
    nomes = {
        "C1": "1ª Coluna",
        "C2": "2ª Coluna",
        "C3": "3ª Coluna"
    }
    return nomes.get(col, col)


def format_par_cols(cols_tuple):
    return f"{format_col_nome(cols_tuple[0])} e {format_col_nome(cols_tuple[1])}"


# =====================================================
# APRENDIZAGEM / AUTÓPSIA PÓS-LOSS
# =====================================================

def tick_learning_cooldowns(session):
    for col in ("C1", "C2", "C3"):
        if session["cooldown_by_col"][col] > 0:
            session["cooldown_by_col"][col] -= 1


def registrar_autopsia_loss(session, cols_apostadas, estrategia, ult_resultado, contexto_cols):
    cols_txt = format_par_cols(cols_apostadas)
    if ult_resultado in ("C1", "C2", "C3") and ult_resultado not in cols_apostadas:
        motivo_erro = f"A mesa puxou para {format_col_nome(ult_resultado)} fora do par {cols_txt}"
    else:
        motivo_erro = f"Falha no par {cols_txt} com resultado {ult_resultado}"

    if estrategia in session["strategy_penalty"]:
        session["strategy_penalty"][estrategia] = min(session["strategy_penalty"][estrategia] + 1, 3)

    for c in cols_apostadas:
        if c in session["cooldown_by_col"]:
            session["cooldown_by_col"][c] = max(session["cooldown_by_col"][c], 3)

    session["error_memory"].append({
        "cols": cols_apostadas,
        "strategy": estrategia,
        "last_outcome": ult_resultado,
        "context": contexto_cols[-6:],
        "diagnosis": motivo_erro
    })
    session["error_memory"] = session["error_memory"][-50:]
    return motivo_erro


def registar_acerto_aprendizagem(session, cols_apostadas, estrategia):
    if estrategia in session["strategy_penalty"] and session["strategy_penalty"][estrategia] > 0:
        session["strategy_penalty"][estrategia] -= 1
    for c in cols_apostadas:
        if c in session["cooldown_by_col"] and session["cooldown_by_col"][c] > 0:
            session["cooldown_by_col"][c] -= 1


# =====================================================
# CÉREBRO DE 2 COLUNAS SEM PROTEÇÃO NO T (COM CONCORDÂNCIA E APRENDIZAGEM)
# =====================================================

def two_columns_brain(session):
    history = session["history"]
    cols_hist = [x for x in history if x in ("C1", "C2", "C3")]
    if len(cols_hist) < 10:
        return None

    ult_10 = cols_hist[-10:]

    pares_validos = [
        ("C1", "C2"),
        ("C1", "C3"),
        ("C2", "C3")
    ]

    scores_par = {par: 0.0 for par in pares_validos}
    razoes_por_par = {par: [] for par in pares_validos}
    estrategias_por_par = {par: set() for par in pares_validos}

    def adicionar_ponto_par(par, pontos, estrategia, motivo):
        if any(session["cooldown_by_col"].get(c, 0) > 0 for c in par):
            return
        penalidade = session["strategy_penalty"].get(estrategia, 0)
        peso_final = max(0.25, pontos - (0.5 * penalidade))
        scores_par[par] += peso_final
        razoes_por_par[par].append(f"[{estrategia}] {motivo}")
        estrategias_por_par[par].add(estrategia)

    # 1. QUEBRA DE COLUNA DOMINANTE (repetição da mesma coluna)
    if len(cols_hist) >= 2 and cols_hist[-1] == cols_hist[-2]:
        col_repetida = cols_hist[-1]
        for par in pares_validos:
            if col_repetida not in par:
                adicionar_ponto_par(
                    par,
                    1.0,
                    "quebra_coluna",
                    f"Quebra de repetição de {format_col_nome(col_repetida)} -> foco em {format_par_cols(par)}"
                )

    # 2. ALTERNÂNCIA DE COLUNAS (ritmo variado entre colunas, se penalidade <= 2)
    if len(cols_hist) >= 4 and session["strategy_penalty"].get("alternancia_colunas", 0) <= 2:
        if (
            cols_hist[-1] != cols_hist[-2]
            and cols_hist[-2] != cols_hist[-3]
            and cols_hist[-3] != cols_hist[-4]
        ):
            for par in pares_validos:
                if cols_hist[-1] not in par:
                    adicionar_ponto_par(
                        par,
                        1.0,
                        "alternancia_colunas",
                        f"Ritmo alternado -> entrada em {format_par_cols(par)}"
                    )

    # 3. ATRASO / MENOR FREQUÊNCIA DE COLUNA NAS ÚLTIMAS 10
    contagens_10 = {
        "C1": ult_10.count("C1"),
        "C2": ult_10.count("C2"),
        "C3": ult_10.count("C3")
    }
    for c in ("C1", "C2", "C3"):
        if contagens_10[c] <= 2:
            for par in pares_validos:
                if c in par:
                    adicionar_ponto_par(
                        par,
                        1.0,
                        "atraso_coluna",
                        f"{format_col_nome(c)} com {contagens_10[c]}/10 saídas -> par {format_par_cols(par)}"
                    )

    # Exige concordância (pelo menos 2 sinais/critérios a favor do mesmo par)
    pares_com_concordancia = [
        par for par in pares_validos if len(razoes_por_par[par]) >= 2
    ]
    if not pares_com_concordancia:
        return None

    ultimo_erro = session["error_memory"][-1] if session["error_memory"] else None

    melhor_par = max(pares_com_concordancia, key=lambda p: scores_par[p])
    melhor_score = scores_par[melhor_par]

    min_score_exigido = 2.0 if (ultimo_erro and ultimo_erro.get("cols") == melhor_par) else 1.5
    if melhor_score < min_score_exigido or len(razoes_por_par[melhor_par]) < 2:
        return None

    prioridade_estrategias = ["quebra_coluna", "atraso_coluna", "alternancia_colunas"]
    estrategia_principal = next(
        (e for e in prioridade_estrategias if e in estrategias_por_par[melhor_par]),
        "quebra_coluna"
    )

    return {
        "cols": melhor_par,
        "strategy": estrategia_principal,
        "reason": " | ".join(razoes_por_par[melhor_par])
    }


# =====================================================
# TESTE ESTATÍSTICO (WILSON LOWER BOUND)
# =====================================================

def wilson_lower_bound(wins, total):
    if total == 0:
        return 0.0

    z = 1.96
    p = wins / total
    denominator = 1 + z * z / total
    center = p + z * z / (2 * total)
    margin = z * sqrt(
        (p * (1 - p) / total)
        + (z * z / (4 * total * total))
    )
    return (center - margin) / denominator


def strategy_validated(session):
    return True


def brain_status(session):
    total = len(session["paper_results"])
    return (
        "MODO REAL ATIVO (SEM FILTRO EXPERIMENTAL)",
        f"Entradas diretas ativas | {total} ciclos concluídos"
    )


# =====================================================
# AVALIAÇÃO DE CICLO (2 COLUNAS, SEM PROTEÇÃO NO T, ATÉ G2)
# =====================================================

def evaluate_paper(session, outcome):
    if outcome == "T":
        session["paper_t"] += 1

    # Fase Gale 2
    if session.get("pending_paper_g2"):
        pred = session["pending_paper_g2"]
        session["pending_paper_g2"] = None

        acertou = (outcome in pred["cols"])
        session["paper_results"].append(acertou)
        session["paper_results"] = session["paper_results"][-1000:]

        strat = pred["strategy"]
        if strat in session["strategy_stats"]:
            session["strategy_stats"][strat]["signals"] += 1
            if acertou:
                session["strategy_stats"][strat]["wins"] += 1
                registar_acerto_aprendizagem(session, pred["cols"], strat)
            else:
                session["strategy_stats"][strat]["losses"] += 1
                registrar_autopsia_loss(session, pred["cols"], strat, outcome, session["history"])
        return

    # Fase Gale 1
    if session.get("pending_paper_g1"):
        pred = session["pending_paper_g1"]
        session["pending_paper_g1"] = None

        if outcome in pred["cols"]:
            session["paper_results"].append(True)
            session["paper_results"] = session["paper_results"][-1000:]
            strat = pred["strategy"]
            if strat in session["strategy_stats"]:
                session["strategy_stats"][strat]["signals"] += 1
                session["strategy_stats"][strat]["wins"] += 1
            registar_acerto_aprendizagem(session, pred["cols"], strat)
        else:
            # Falhou no Gale 1 -> passa para Gale 2
            session["pending_paper_g2"] = pred
        return

    # Fase Entrada inicial
    pred = session.get("pending_paper")
    if not pred:
        return

    session["pending_paper"] = None

    if outcome in pred["cols"]:
        session["paper_results"].append(True)
        session["paper_results"] = session["paper_results"][-1000:]
        strat = pred["strategy"]
        if strat in session["strategy_stats"]:
            session["strategy_stats"][strat]["signals"] += 1
            session["strategy_stats"][strat]["wins"] += 1
        registar_acerto_aprendizagem(session, pred["cols"], strat)
    else:
        # Falhou na Entrada -> passa para Gale 1 normal
        session["pending_paper_g1"] = pred


# =====================================================
# GESTÃO DAS OPERAÇÕES REAIS (2 COLUNAS, SEM PROTEÇÃO NO T, ATÉ G2)
# =====================================================

def close_cycle(session):
    session["active_cols"] = None
    session["active_reason"] = ""
    session["active_strategy"] = ""
    session["gale"] = 0


def process_live_bet(chat_id, session, outcome, raw_label):
    cols = session["active_cols"]
    if cols is None:
        return

    if outcome == "T":
        session["stats"]["t_hits"] += 1

    # ACERTO EM UMA DAS DUAS COLUNAS ESCOLHIDAS
    if outcome in cols:
        strat = session["active_strategy"]
        if session["gale"] == 0:
            session["stats"]["wins"] += 1
            nivel = "ENTRADA PRINCIPAL"
        elif session["gale"] == 1:
            session["stats"]["wins"] += 1
            session["stats"]["wins_g1"] += 1
            nivel = "GALE 1 (G1)"
        else:
            session["stats"]["wins"] += 1
            session["stats"]["wins_g2"] += 1
            nivel = "GALE 2 (G2)"

        registar_acerto_aprendizagem(session, cols, strat)
        close_cycle(session)

        bot.send_message(
            chat_id,
            "🟢 *GREEN / VITÓRIA CONFIRMADA!* ✨\n\n"
            f"🏆 Resolução: {nivel}\n"
            f"🎯 Resultado: {raw_label} ({outcome})\n"
            f"🧱 Colunas: {format_par_cols(cols)}\n\n"
            "Ciclo encerrado com sucesso.",
            parse_mode="Markdown"
        )
        return

    # FALHA NA ENTRADA -> VAI PARA GALE 1 (G1) NORMAL
    if session["gale"] == 0:
        session["gale"] = 1
        total_g1 = GALE1_COLUNA * 2

        bot.send_message(
            chat_id,
            "🔴 *LOSS NA ENTRADA PRINCIPAL*\n\n"
            "🔄 **GALE 1 (G1)** 🚨\n\n"
            f"🧱 Colunas: *{format_par_cols(cols)}*\n"
            f"💰 Aposta: {GALE1_COLUNA}€ em cada coluna (Total: {total_g1}€)\n"
            "Sem proteção no empate | Próximo passo: Gale 2.",
            parse_mode="Markdown"
        )
        return

    # FALHA NO GALE 1 -> VAI PARA GALE 2 (G2)
    if session["gale"] == 1:
        session["gale"] = 2
        total_g2 = GALE2_COLUNA * 2

        bot.send_message(
            chat_id,
            "🔴 *LOSS NO GALE 1 (G1)*\n\n"
            "🔄 **GALE 2 (G2)** 🚨\n\n"
            f"🧱 Colunas: *{format_par_cols(cols)}*\n"
            f"💰 Aposta: {GALE2_COLUNA}€ em cada coluna (Total: {total_g2}€)\n"
            "Sem proteção no empate | Último Gale do ciclo.",
            parse_mode="Markdown"
        )
        return

    # FALHA NO GALE 2 -> AUTÓPSIA DO ERRO E PERDA FINAL DO CICLO
    strat = session["active_strategy"]
    diagnostico = registrar_autopsia_loss(session, cols, strat, outcome, session["history"])
    session["stats"]["losses"] += 1
    close_cycle(session)
    losses = session["stats"]["losses"]

    if losses >= LIMITE_LOSSES:
        session["blocked"] = True
        bot.send_message(
            chat_id,
            "🚨 *LIMITE DE PERDAS ATINGIDO!* 🛑\n\n"
            f"🔴 Perdas finais: {losses}/{LIMITE_LOSSES}\n"
            f"🧠 Autópsia do erro: {diagnostico}\n\n"
            "🛑 Sessão bloqueada de imediato.\n"
            "Utiliza /reset para iniciar uma nova sessão.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id,
            "❌ *LOSS FINAL - GALE 2 FALHADO*\n\n"
            f"🔴 Perdas finais: {losses}/{LIMITE_LOSSES}\n"
            f"🧠 Autópsia e aprendizagem: {diagnostico}\n\n"
            "O cérebro ajustou os pesos e arrefeceu este padrão para não repetir o mesmo erro.",
            parse_mode="Markdown"
        )


# =====================================================
# GERAR NOVA DECISÃO DE 2 COLUNAS (SEM PROTEÇÃO NO T)
# =====================================================

def generate_decision(chat_id, session):
    if session["blocked"] or session["active_cols"] is not None:
        return

    if (
        session["pending_paper"] is not None
        or session.get("pending_paper_g1") is not None
        or session.get("pending_paper_g2") is not None
    ):
        return

    candidate = two_columns_brain(session)

    if candidate is None:
        session["stats"]["observations"] += 1
        return

    session["pending_paper"] = candidate

    cols = candidate["cols"]
    session["active_cols"] = cols
    session["active_reason"] = candidate["reason"]
    session["active_strategy"] = candidate["strategy"]
    session["gale"] = 0
    session["stats"]["entries"] += 1

    total_entrada = ENTRADA_COLUNA * 2
    total_g1 = GALE1_COLUNA * 2
    total_g2 = GALE2_COLUNA * 2

    bot.send_message(
        chat_id,
        "🧠 *TWO COLUMNS BRAIN*\n\n"
        "⚡ ENTRADA REAL IMEDIATA (SEM FILTRO EXPERIMENTAL)\n\n"
        f"🧱 Entrar em: *{format_par_cols(cols)}*\n"
        f"💰 Entrada: {ENTRADA_COLUNA}€ por coluna (Total: {total_entrada}€)\n"
        f"🔄 Gale 1: {GALE1_COLUNA}€ por coluna (Total: {total_g1}€)\n"
        f"🔄 Gale 2: {GALE2_COLUNA}€ por coluna (Total: {total_g2}€)\n"
        "Sem proteção no empate | Até Gale 2\n\n"
        f"🔎 Estratégia: {candidate['strategy']}\n"
        f"💡 Motivo: {candidate['reason']}",
        parse_mode="Markdown"
    )


# =====================================================
# RECEBER UMA NOVA JOGADA
# =====================================================

def receive_result(chat_id, session, outcome, raw_label):
    tick_learning_cooldowns(session)
    evaluate_paper(session, outcome)
    process_live_bet(chat_id, session, outcome, raw_label)

    session["history"].append(outcome)
    session["history"] = session["history"][-250:]

    if not session["blocked"]:
        generate_decision(chat_id, session)


# =====================================================
# COMANDOS DO BOT
# =====================================================

@bot.message_handler(commands=["start"])
def start(message):
    sessions[message.chat.id] = nova_sessao()
    total_entrada = ENTRADA_COLUNA * 2
    total_g1 = GALE1_COLUNA * 2
    total_g2 = GALE2_COLUNA * 2

    bot.reply_to(
        message,
        "🤖 *TWO COLUMNS BRAIN*\n\n"
        "Sistema de 2 Colunas (C1+C2 / C1+C3) sem proteção no empate, até Gale 2, aprendizagem pós-loss e entradas reais imediatas!\n\n"
        f"📊 Envia as tuas {JANELA} jogadas iniciais (números 0-36 ou C1/C2/C3).\n\n"
        "Exemplo:\n"
        "`34 5 17 31 3 17 14 21 8 12`\n\n"
        f"💰 Entrada: {ENTRADA_COLUNA}€ x 2 col ({total_entrada}€) | 🔄 G1: {GALE1_COLUNA}€ x 2 col ({total_g1}€) | 🔄 G2: {GALE2_COLUNA}€ x 2 col ({total_g2}€)\n"
        "Sem proteção no empate | Até Gale 2\n"
        f"🚨 Máximo: {LIMITE_LOSSES} perdas finais\n\n"
        "/stats - Estatísticas detalhadas\n"
        "/status - Estado do cérebro e aprendizagem\n"
        "/reset - Reiniciar sessão\n"
        "/ajuda - Ajuda",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["ajuda"])
def help_command(message):
    bot.reply_to(
        message,
        "📖 *COMO UTILIZAR*\n\n"
        f"1. Utiliza /start.\n"
        f"2. Envia exatamente {JANELA} jogadas iniciais (ex: números de 0 a 36 ou C1, C2, C3).\n"
        "3. Depois envia apenas uma jogada de cada vez.\n"
        "4. O robô manda sempre duas colunas sem proteção no empate e aprende com os losses.\n\n"
        "C1 = 1ª Coluna | C2 = 2ª Coluna | C3 = 3ª Coluna",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["status"])
def status_command(message):
    session = sessions.get(message.chat.id)
    if session is None:
        bot.reply_to(message, "Utiliza /start primeiro.")
        return

    status, detail = brain_status(session)
    ativa_txt = format_par_cols(session["active_cols"]) if session["active_cols"] else "NÃO"
    ultimo_erro = session["error_memory"][-1]["diagnosis"] if session["error_memory"] else "Nenhum loss registado ainda"

    bot.reply_to(
        message,
        "🧠 *ESTADO DO TWO COLUMNS BRAIN*\n\n"
        f"📊 Estado: {status}\n"
        f"🔎 {detail}\n"
        f"📜 Histórico: {len(session['history'])} jogadas\n"
        f"🎯 Ciclos concluídos: {len(session['paper_results'])}\n"
        f"⚡ Operação ativa: {ativa_txt}\n"
        f"🧩 Erros analisados: {len(session['error_memory'])}\n"
        f"🔍 Última autópsia: {ultimo_erro}\n"
        f"🚨 Bloqueado: {'SIM' if session['blocked'] else 'NÃO'}",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["stats"])
def stats_command(message):
    session = sessions.get(message.chat.id)
    if session is None:
        bot.reply_to(message, "Utiliza /start primeiro.")
        return

    st = session["stats"]
    resolvidas = st["wins"] + st["losses"]
    taxa_real = (st["wins"] / resolvidas * 100) if resolvidas else 0.0

    paper = session["paper_results"]
    taxa_papel = (sum(paper) / len(paper) * 100) if paper else 0.0
    recentes = paper[-MIN_RECENTES:] if paper else []
    taxa_recente = (sum(recentes) / len(recentes) * 100) if recentes else 0.0
    wilson = (wilson_lower_bound(sum(paper), len(paper)) * 100) if paper else 0.0

    strat_text = ""
    for s_name, s_data in session["strategy_stats"].items():
        s_tot = s_data["wins"] + s_data["losses"]
        s_rate = (s_data["wins"] / s_tot * 100) if s_tot else 0.0
        pen = session["strategy_penalty"].get(s_name, 0)
        strat_text += f"• *{s_name}*: {s_data['wins']}W / {s_data['losses']}L ({s_rate:.1f}%) | Penalidade: {pen}\n"

    bot.reply_to(
        message,
        "📊 *RELATÓRIO TWO COLUMNS BRAIN*\n\n"
        "OPERAÇÕES REAIS\n"
        f"🟢 Greens: {st['wins']} (G1: {st['wins_g1']} | G2: {st['wins_g2']})\n"
        f"🔴 Perdas finais: {st['losses']}/{LIMITE_LOSSES}\n"
        f"🎯 Entradas: {st['entries']}\n"
        f"📈 Taxa de acerto real: {taxa_real:.2f}%\n\n"
        "HISTÓRICO DE CICLOS\n"
        f"📊 Total ciclos concluídos: {len(paper)}\n"
        f"📈 Taxa global: {taxa_papel:.2f}%\n"
        f"📈 Taxa últimas {MIN_RECENTES}: {taxa_recente:.2f}%\n"
        f"📉 Limite inferior Wilson: {wilson:.2f}%\n\n"
        "DESEMPENHO E APRENDIZAGEM POR ESTRATÉGIA\n"
        f"{strat_text}\n"
        f"Estado da validação: {brain_status(session)[0]}",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["reset"])
def reset_command(message):
    sessions[message.chat.id] = nova_sessao()
    bot.reply_to(
        message,
        f"🔄 Sessão reiniciada!\n\n"
        f"Envia novamente as {JANELA} jogadas iniciais."
    )


# =====================================================
# RECEBER RESULTADOS DA MESA
# =====================================================

@bot.message_handler(
    func=lambda m: True,
    content_types=["text"]
)
def handle_results(message):
    chat_id = message.chat.id
    session = sessions.get(chat_id)

    if session is None:
        bot.reply_to(message, "Utiliza /start para iniciar o bot.")
        return

    if session["blocked"]:
        bot.reply_to(
            message,
            "🛑 Sessão bloqueada.\nUtiliza /reset para iniciar outra."
        )
        return

    tokens = re.findall(r"C[123]|T|\d+", message.text.upper())
    if not tokens:
        bot.reply_to(
            message,
            "⚠️ Formato inválido.\nUtiliza números de 0 a 36 ou C1, C2, C3."
        )
        return

    parsed = []
    for tk in tokens:
        outcome = parse_token_to_outcome(tk)
        if outcome is None:
            bot.reply_to(
                message,
                f"⚠️ Valor inválido: `{tk}`.\nUsa números de 0 a 36 ou C1, C2, C3.",
                parse_mode="Markdown"
            )
            return
        parsed.append((tk, outcome))

    # PRIMEIRO ENVIO: 10 JOGADAS INICIAIS
    if session["awaiting_seed"]:
        if len(parsed) != JANELA:
            bot.reply_to(
                message,
                f"⚠️ Preciso de exatamente {JANELA} jogadas iniciais. Tens {len(parsed)}."
            )
            return

        session["history"] = [col for _, col in parsed]
        session["awaiting_seed"] = False

        bot.reply_to(
            message,
            "🧠 *HISTÓRICO CARREGADO!* 🚀\n\n"
            f"As {JANELA} jogadas foram guardadas.\n"
            "Envia agora **apenas UMA nova jogada** de cada vez para começar a analisar e dar entradas reais.",
            parse_mode="Markdown"
        )
        return

    # FLUXO NORMAL: UMA JOGADA DE CADA VEZ
    if len(parsed) != 1:
        bot.reply_to(
            message,
            "⚠️ Envia apenas um resultado por mensagem (ex: 34 ou C1)."
        )
        return

    raw_label, outcome = parsed[0]
    receive_result(chat_id, session, outcome, raw_label)

    bot.reply_to(
        message,
        f"✅ Jogada `{raw_label}` ({outcome}) registada! Histórico ativo: `{len(session['history'])}` rondas. A analisar...",
        parse_mode="Markdown"
    )


# =====================================================
# INICIALIZAÇÃO DO BOT
# =====================================================

if __name__ == "__main__":
    print("TWO COLUMNS BRAIN ONLINE")

    Thread(
        target=run_web,
        daemon=True
    ).start()

    bot.infinity_polling(
        skip_pending=True,
        timeout=20,
        long_polling_timeout=20
    )
