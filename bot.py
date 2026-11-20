import os
import re
from math import sqrt
from threading import Thread

import telebot
from flask import Flask

# =====================================================
# SINGLE COLUMN + T PROTECTION - ADAPTIVE LEARNING BRAIN
# Motor de 1 Coluna (C1 / C2 / C3) + Proteção no T, Martingale até G1 e Aprendizagem Pós-Loss
# =====================================================

TOKEN = os.getenv(
    "BOT_TOKEN",
    "8922303337:AAEfiGQK15Cd4B4SsW-FS97Fq6QyPH2aUEs"
)

if not TOKEN or TOKEN == "COLOCA_AQUI_O_TEU_TOKEN_NOVO":
    raise ValueError("Configura o teu token do Telegram através da variável BOT_TOKEN.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# CONFIGURAÇÕES DE GESTÃO DE BANCA E RISCO (1 COLUNA + PROTEÇÃO NO T)
ENTRADA_COLUNA = 4      # Aposta base na coluna escolhida (Entrada)
ENTRADA_T = 2           # Proteção no T na Entrada

GALE1_COLUNA = 8        # Aposta na coluna escolhida no Gale 1 (G1)
GALE1_T = 4             # Proteção no T no Gale 1 (G1)

JANELA = 10             # Jogadas iniciais para arrancar
LIMITE_LOSSES = 2       # Máximo de ciclos perdidos (Entrada + G1 falhados)

MIN_PAPER = 0           # Sem filtro experimental prévio: entra logo em real
MIN_RECENTES = 10       # Janela recente para consulta de estatísticas

# Sessões em memória por chat
sessions = {}


# =====================================================
# SERVIDOR WEB (RENDER 24/7)
# =====================================================

@app.route("/")
def home():
    return "SINGLE COLUMN + T PROTECTION BRAIN - ONLINE 24/7, ZÉ!"


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

        "active_col": None,     # Ex: "C1", "C2" ou "C3" (sempre apenas UMA coluna)
        "active_reason": "",
        "active_strategy": "",
        "gale": 0,              # 0 = Entrada, 1 = Gale 1
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
            "losses": 0,
            "t_hits": 0,
            "entries": 0,
            "observations": 0
        }
    }


# =====================================================
# CONVERSÃO DE RESULTADO PARA COLUNA / T
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


# =====================================================
# APRENDIZAGEM / AUTÓPSIA PÓS-LOSS
# =====================================================

def tick_learning_cooldowns(session):
    for col in ("C1", "C2", "C3"):
        if session["cooldown_by_col"][col] > 0:
            session["cooldown_by_col"][col] -= 1


def registrar_autopsia_loss(session, col_apostada, estrategia, ult_resultado, contexto_cols):
    # Analisa o porquê do loss e ajusta pesos/arrefecimento para não repetir o mesmo erro
    if ult_resultado == "T":
        motivo_erro = f"Saiu T mas a proteção não segurou o ciclo na {format_col_nome(col_apostada)}"
    elif ult_resultado in ("C1", "C2", "C3") and ult_resultado != col_apostada:
        motivo_erro = f"A mesa puxou para {format_col_nome(ult_resultado)} em vez de {format_col_nome(col_apostada)}"
    else:
        motivo_erro = f"Falha em {format_col_nome(col_apostada)} com resultado {ult_resultado}"

    # Aumenta penalização da estratégia que falhou e coloca arrefecimento na coluna que levou loss
    if estrategia in session["strategy_penalty"]:
        session["strategy_penalty"][estrategia] = min(session["strategy_penalty"][estrategia] + 1, 3)

    if col_apostada in session["cooldown_by_col"]:
        session["cooldown_by_col"][col_apostada] = max(session["cooldown_by_col"][col_apostada], 3)

    session["error_memory"].append({
        "col": col_apostada,
        "strategy": estrategia,
        "last_outcome": ult_resultado,
        "context": contexto_cols[-6:],
        "diagnosis": motivo_erro
    })
    session["error_memory"] = session["error_memory"][-50:]
    return motivo_erro


def registar_acerto_aprendizagem(session, col_apostada, estrategia):
    # Quando acerta, alivia gradualmente a penalização da estratégia e reduz arrefecimento
    if estrategia in session["strategy_penalty"] and session["strategy_penalty"][estrategia] > 0:
        session["strategy_penalty"][estrategia] -= 1
    if col_apostada in session["cooldown_by_col"] and session["cooldown_by_col"][col_apostada] > 0:
        session["cooldown_by_col"][col_apostada] -= 1


# =====================================================
# CÉREBRO DE 1 COLUNA + PROTEÇÃO NO T (COM APRENDIZAGEM)
# =====================================================

def single_column_brain(session):
    history = session["history"]
    cols_hist = [x for x in history if x in ("C1", "C2", "C3")]
    if len(cols_hist) < 10:
        return None

    ult_10 = cols_hist[-10:]

    scores_col = {"C1": 0.0, "C2": 0.0, "C3": 0.0}
    razoes_por_col = {"C1": [], "C2": [], "C3": []}
    estrategia_por_col = {}

    def adicionar_ponto(col, pontos, estrategia, motivo):
        if session["cooldown_by_col"].get(col, 0) > 0:
            return
        penalidade = session["strategy_penalty"].get(estrategia, 0)
        peso_final = max(0.25, pontos - (0.5 * penalidade))
        scores_col[col] += peso_final
        razoes_por_col[col].append(f"[{estrategia}] {motivo}")
        if col not in estrategia_por_col:
            estrategia_por_col[col] = estrategia

    # 1. QUEBRA DE COLUNA DOMINANTE (repetição da mesma coluna)
    if len(cols_hist) >= 2 and cols_hist[-1] == cols_hist[-2]:
        col_repetida = cols_hist[-1]
        for c in ("C1", "C2", "C3"):
            if c != col_repetida:
                adicionar_ponto(
                    c,
                    1.0,
                    "quebra_coluna",
                    f"Quebra de repetição de {format_col_nome(col_repetida)} -> foco em {format_col_nome(c)} + T"
                )

    # 2. ALTERNÂNCIA DE COLUNAS (ritmo variado entre colunas)
    if len(cols_hist) >= 4:
        if (
            cols_hist[-1] != cols_hist[-2]
            and cols_hist[-2] != cols_hist[-3]
            and cols_hist[-3] != cols_hist[-4]
        ):
            for c in ("C1", "C2", "C3"):
                if c != cols_hist[-1]:
                    adicionar_ponto(
                        c,
                        1.0,
                        "alternancia_colunas",
                        f"Ritmo alternado -> entrada em {format_col_nome(c)} + T"
                    )

    # 3. ATRASO / MENOR FREQUÊNCIA DE COLUNA NAS ÚLTIMAS 10
    contagens_10 = {
        "C1": ult_10.count("C1"),
        "C2": ult_10.count("C2"),
        "C3": ult_10.count("C3")
    }
    for c in ("C1", "C2", "C3"):
        if contagens_10[c] <= 2:
            adicionar_ponto(
                c,
                1.0,
                "atraso_coluna",
                f"{format_col_nome(c)} com apenas {contagens_10[c]}/10 saídas -> entrada + T"
            )

    # Verifica se houve erro recente parecido para exigir mais força
    ultimo_erro = session["error_memory"][-1] if session["error_memory"] else None

    melhor_col = max(scores_col, key=scores_col.get)
    melhor_score = scores_col[melhor_col]

    # Exige pelo menos 1.5 pontos de pontuação (ou 2.0 se o último erro foi nessa mesma coluna)
    min_score_exigido = 2.0 if (ultimo_erro and ultimo_erro["col"] == melhor_col) else 1.5
    if melhor_score < min_score_exigido or not razoes_por_col[melhor_col]:
        return None

    return {
        "col": melhor_col,
        "strategy": estrategia_por_col.get(melhor_col, "quebra_coluna"),
        "reason": " | ".join(razoes_por_col[melhor_col])
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
    # Sem filtro experimental prévio: entra direto em operações reais
    return True


def brain_status(session):
    total = len(session["paper_results"])
    return (
        "MODO REAL ATIVO (SEM FILTRO EXPERIMENTAL)",
        f"Entradas diretas ativas | {total} ciclos concluídos"
    )


# =====================================================
# AVALIAÇÃO DE CICLO (COM G1 + PROTEÇÃO NO T)
# =====================================================

def evaluate_paper(session, outcome):
    if outcome == "T":
        session["paper_t"] += 1

    # Fase Gale 1
    if session.get("pending_paper_g1"):
        pred = session["pending_paper_g1"]
        session["pending_paper_g1"] = None

        acertou = (outcome == pred["col"] or outcome == "T")
        session["paper_results"].append(acertou)
        session["paper_results"] = session["paper_results"][-1000:]

        strat = pred["strategy"]
        if strat in session["strategy_stats"]:
            session["strategy_stats"][strat]["signals"] += 1
            if acertou:
                session["strategy_stats"][strat]["wins"] += 1
                registar_acerto_aprendizagem(session, pred["col"], strat)
            else:
                session["strategy_stats"][strat]["losses"] += 1
                registrar_autopsia_loss(session, pred["col"], strat, outcome, session["history"])
        return

    # Fase Entrada inicial
    pred = session.get("pending_paper")
    if not pred:
        return

    session["pending_paper"] = None

    if outcome == pred["col"] or outcome == "T":
        session["paper_results"].append(True)
        session["paper_results"] = session["paper_results"][-1000:]
        strat = pred["strategy"]
        if strat in session["strategy_stats"]:
            session["strategy_stats"][strat]["signals"] += 1
            session["strategy_stats"][strat]["wins"] += 1
        registar_acerto_aprendizagem(session, pred["col"], strat)
    else:
        # Falhou na Entrada -> passa para Gale 1 com proteção no T
        session["pending_paper_g1"] = pred


# =====================================================
# GESTÃO DAS OPERAÇÕES REAIS (1 COLUNA + PROTEÇÃO NO T, ATÉ G1)
# =====================================================

def close_cycle(session):
    session["active_col"] = None
    session["active_reason"] = ""
    session["active_strategy"] = ""
    session["gale"] = 0


def process_live_bet(chat_id, session, outcome, raw_label):
    col = session["active_col"]
    if col is None:
        return

    if outcome == "T":
        session["stats"]["t_hits"] += 1

    # ACERTO NA COLUNA ESCOLHIDA OU PROTEÇÃO NO T
    if outcome == col or outcome == "T":
        strat = session["active_strategy"]
        if session["gale"] == 0:
            session["stats"]["wins"] += 1
            nivel = "ENTRADA PRINCIPAL"
        else:
            session["stats"]["wins"] += 1
            session["stats"]["wins_g1"] += 1
            nivel = "GALE 1 (G1)"

        protecao_txt = " (Proteção no T ativada)" if outcome == "T" else ""
        registar_acerto_aprendizagem(session, col, strat)
        close_cycle(session)

        bot.send_message(
            chat_id,
            "🟢 *GREEN / VITÓRIA CONFIRMADA!* ✨\n\n"
            f"🏆 Resolução: {nivel}{protecao_txt}\n"
            f"🎯 Resultado: {raw_label} ({outcome})\n"
            f"🧱 Coluna: {format_col_nome(col)} + Proteção no T\n\n"
            "Ciclo encerrado com sucesso.",
            parse_mode="Markdown"
        )
        return

    # FALHA NA ENTRADA -> VAI PARA GALE 1 (G1) COM PROTEÇÃO NO T
    if session["gale"] == 0:
        session["gale"] = 1
        total_g1 = GALE1_COLUNA + GALE1_T

        bot.send_message(
            chat_id,
            "🔴 *LOSS NA ENTRADA PRINCIPAL*\n\n"
            "🔄 **GALE 1 (G1) COM PROTEÇÃO NO T** 🚨\n\n"
            f"🧱 Coluna: *{format_col_nome(col)}*\n"
            f"💰 Aposta: {GALE1_COLUNA}€ na coluna + {GALE1_T}€ no T (Total: {total_g1}€)\n"
            "🛡️ Proteção no T ativa | Sem Gale 2.",
            parse_mode="Markdown"
        )
        return

    # FALHA NO GALE 1 -> AUTÓPSIA DO ERRO E PERDA FINAL DO CICLO
    strat = session["active_strategy"]
    diagnostico = registrar_autopsia_loss(session, col, strat, outcome, session["history"])
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
            "❌ *LOSS FINAL - GALE 1 FALHADO*\n\n"
            f"🔴 Perdas finais: {losses}/{LIMITE_LOSSES}\n"
            f"🧠 Autópsia e aprendizagem: {diagnostico}\n\n"
            "O cérebro ajustou os pesos e arrefeceu este padrão para não repetir o mesmo erro.",
            parse_mode="Markdown"
        )


# =====================================================
# GERAR NOVA DECISÃO DE 1 COLUNA + PROTEÇÃO NO T
# =====================================================

def generate_decision(chat_id, session):
    if session["blocked"] or session["active_col"] is not None:
        return

    if session["pending_paper"] is not None or session.get("pending_paper_g1") is not None:
        return

    candidate = single_column_brain(session)

    if candidate is None:
        session["stats"]["observations"] += 1
        return

    session["pending_paper"] = candidate

    col = candidate["col"]
    session["active_col"] = col
    session["active_reason"] = candidate["reason"]
    session["active_strategy"] = candidate["strategy"]
    session["gale"] = 0
    session["stats"]["entries"] += 1

    total_entrada = ENTRADA_COLUNA + ENTRADA_T
    total_g1 = GALE1_COLUNA + GALE1_T

    bot.send_message(
        chat_id,
        "🧠 *SINGLE COLUMN + T PROTECTION BRAIN*\n\n"
        "⚡ ENTRADA REAL IMEDIATA (SEM FILTRO EXPERIMENTAL)\n\n"
        f"🧱 Entrar em: *{format_col_nome(col)}* + *Proteção no T*\n"
        f"💰 Entrada: {ENTRADA_COLUNA}€ na coluna + {ENTRADA_T}€ no T (Total: {total_entrada}€)\n"
        f"🔄 Gale 1: {GALE1_COLUNA}€ na coluna + {GALE1_T}€ no T (Total: {total_g1}€)\n"
        "🛡️ Proteção no T ativa | Até Gale 1\n\n"
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
    total_entrada = ENTRADA_COLUNA + ENTRADA_T
    total_g1 = GALE1_COLUNA + GALE1_T

    bot.reply_to(
        message,
        "🤖 *SINGLE COLUMN + T PROTECTION BRAIN*\n\n"
        "Sistema de 1 Coluna (C1 / C2 / C3) com Proteção no T, até Gale 1, aprendizagem pós-loss e entradas reais imediatas!\n\n"
        f"📊 Envia as tuas {JANELA} jogadas iniciais (números 0-36 ou C1/C2/C3/T).\n\n"
        "Exemplo:\n"
        "`34 5 17 31 3 17 14 21 8 12`\n\n"
        f"💰 Entrada: {ENTRADA_COLUNA}€ col + {ENTRADA_T}€ T ({total_entrada}€) | 🔄 G1: {GALE1_COLUNA}€ col + {GALE1_T}€ T ({total_g1}€)\n"
        "🛡️ Proteção no T ativa | Sem Gale 2\n"
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
        f"2. Envia exatamente {JANELA} jogadas iniciais (ex: números de 0 a 36 ou C1, C2, C3, T).\n"
        "3. Depois envia apenas uma jogada de cada vez.\n"
        "4. O robô manda sempre apenas UMA coluna com proteção no T, entra logo em real e aprende com os losses.\n\n"
        "T = Empate / Proteção | C1 = 1ª Coluna | C2 = 2ª Coluna | C3 = 3ª Coluna",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["status"])
def status_command(message):
    session = sessions.get(message.chat.id)
    if session is None:
        bot.reply_to(message, "Utiliza /start primeiro.")
        return

    status, detail = brain_status(session)
    ativa_txt = f"{format_col_nome(session['active_col'])} + T" if session["active_col"] else "NÃO"
    ultimo_erro = session["error_memory"][-1]["diagnosis"] if session["error_memory"] else "Nenhum loss registado ainda"

    bot.reply_to(
        message,
        "🧠 *ESTADO DO SINGLE COLUMN BRAIN*\n\n"
        f"📊 Estado: {status}\n"
        f"🔎 {detail}\n"
        f"📜 Histórico: {len(session['history'])} jogadas\n"
        f"🎯 Ciclos concluídos: {len(session['paper_results'])}\n"
        f"🛡️ T detetados: {session['paper_t']}\n"
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
        "📊 *RELATÓRIO SINGLE COLUMN BRAIN*\n\n"
        "OPERAÇÕES REAIS\n"
        f"🟢 Greens: {st['wins']} (G1: {st['wins_g1']})\n"
        f"🔴 Perdas finais: {st['losses']}/{LIMITE_LOSSES}\n"
        f"🛡️ Proteções T batidas: {st['t_hits']}\n"
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
            "⚠️ Formato inválido.\nUtiliza números de 0 a 36 ou C1, C2, C3, T."
        )
        return

    parsed = []
    for tk in tokens:
        outcome = parse_token_to_outcome(tk)
        if outcome is None:
            bot.reply_to(
                message,
                f"⚠️ Valor inválido: `{tk}`.\nUsa números de 0 a 36 ou C1, C2, C3, T.",
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
            "⚠️ Envia apenas um resultado por mensagem (ex: 34, C1 ou T)."
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
    print("SINGLE COLUMN + T PROTECTION BRAIN ONLINE")

    Thread(
        target=run_web,
        daemon=True
    ).start()

    bot.infinity_polling(
        skip_pending=True,
        timeout=20,
        long_polling_timeout=20
    )
