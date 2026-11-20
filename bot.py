import os
import re
from math import sqrt
from threading import Thread

import telebot
from flask import Flask

# =====================================================
# ROULETTE COLUMNS - MULTISTRATEGY BRAIN
# Motor de 2 Colunas (1ª e 2ª / 1ª e 3ª), Martingale Sprint até G1, Sem Proteção no 0
# =====================================================

TOKEN = os.getenv(
    "BOT_TOKEN",
    "8922303337:AAEfiGQK15Cd4B4SsW-FS97Fq6QyPH2aUEs"
)

if not TOKEN or TOKEN == "COLOCA_AQUI_O_TEU_TOKEN_NOVO":
    raise ValueError("Configura o teu token do Telegram através da variável BOT_TOKEN.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# CONFIGURAÇÕES DE GESTÃO DE BANCA E RISCO (POR CADA COLUNA DAS 2 ESCOLHIDAS)
ENTRADA_COLUNA = 3      # Ex: 3€ na 1ª coluna + 3€ na 2ª coluna (total 6€ na Entrada)
GALE1_COLUNA = 6        # Ex: 6€ na 1ª coluna + 6€ na 2ª coluna (total 12€ no G1)

JANELA = 10             # Jogadas iniciais para arrancar
LIMITE_LOSSES = 2       # Máximo de ciclos perdidos (Entrada + G1 falhados)

MIN_PAPER = 10          # Simulações mínimas em papel
MIN_RECENTES = 10       # Janela recente para avaliação

# Sessões em memória por chat
sessions = {}


# =====================================================
# SERVIDOR WEB (RENDER 24/7)
# =====================================================

@app.route("/")
def home():
    return "ROULETTE 2 COLUMNS BRAIN - ONLINE 24/7, ZÉ!"


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
        "history": [],          # Lista de números ("0" a "36") ou colunas ("C1", "C2", "C3", "Z")
        "awaiting_seed": True,

        "active_cols": None,    # Ex: ("C1", "C2") ou ("C1", "C3")
        "gale": 0,              # 0 = Entrada, 1 = Gale 1
        "blocked": False,

        # Fila de simulação em papel (suporta ciclo Entrada -> G1)
        "pending_paper": None,
        "pending_paper_g1": None,

        # Resultados globais da simulação em tempo real
        "paper_results": [],
        "paper_zeros": 0,

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
            "zeros": 0,
            "entries": 0,
            "observations": 0
        }
    }


# =====================================================
# CONVERSÃO DE NÚMERO (0-36) PARA COLUNA (C1, C2, C3, Z)
# =====================================================

C1_NUMS = {1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34}
C2_NUMS = {2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35}
C3_NUMS = {3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36}


def parse_token_to_col(token):
    t = token.strip().upper()
    if t in ("C1", "1", "1A", "COL1"):
        return "C1"
    if t in ("C2", "2", "2A", "COL2"):
        return "C2"
    if t in ("C3", "3", "3A", "COL3"):
        return "C3"
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


def format_cols_nome(cols):
    nomes = {
        "C1": "1ª Coluna",
        "C2": "2ª Coluna",
        "C3": "3ª Coluna"
    }
    return f"{nomes[cols[0]]} e {nomes[cols[1]]}"


def outras_duas_colunas(col_excluida):
    # Devolve sempre um par válido de duas colunas ("C1","C2") ou ("C1","C3") ou ("C2","C3")
    if col_excluida == "C3":
        return ("C1", "C2")
    if col_excluida == "C2":
        return ("C1", "C3")
    return ("C2", "C3")


# =====================================================
# CÉREBRO DE 2 COLUNAS (4 FATORES / MAIORIA DE CONCORDÂNCIA)
# =====================================================

def roulette_columns_brain(history):
    cols_hist = [x for x in history if x in ("C1", "C2", "C3")]
    if len(cols_hist) < 12:
        return None

    ult_6 = cols_hist[-6:]
    ult_12 = cols_hist[-12:]

    votos_pares = {}
    razoes_por_par = {}

    def adicionar_voto(par, estrategia, motivo):
        votos_pares[par] = votos_pares.get(par, 0) + 1
        razoes_por_par.setdefault(par, []).append(f"[{estrategia}] {motivo}")

    # 1. QUEBRA DE COLUNA DOMINANTE
    # Se a última coluna repetiu pelo menos 2x seguidas, aponta para as outras 2 colunas
    if len(cols_hist) >= 2 and cols_hist[-1] == cols_hist[-2]:
        par_quebra = outras_duas_colunas(cols_hist[-1])
        adicionar_voto(
            par_quebra,
            "quebra_coluna",
            f"Repetição em {cols_hist[-1]} -> cobertura em {format_cols_nome(par_quebra)}"
        )

    # 2. ALTERNÂNCIA DE COLUNAS (PING-PONG ENTRE COLUNAS)
    if len(cols_hist) >= 4:
        if (
            cols_hist[-1] != cols_hist[-2]
            and cols_hist[-2] != cols_hist[-3]
            and cols_hist[-3] != cols_hist[-4]
        ):
            # Evita repetir a última coluna que acabou de sair
            par_alt = outras_duas_colunas(cols_hist[-1])
            adicionar_voto(
                par_alt,
                "alternancia_colunas",
                f"Alternância detetada -> foco em {format_cols_nome(par_alt)}"
            )

    # 3. ATRASO / MENOR FREQUÊNCIA DE COLUNA NAS ÚLTIMAS 12
    contagens_12 = {
        "C1": ult_12.count("C1"),
        "C2": ult_12.count("C2"),
        "C3": ult_12.count("C3")
    }
    col_menos_frequente = min(contagens_12, key=contagens_12.get)
    # Se houver uma coluna claramente atrasada (<= 2 saídas em 12), escolhe as outras 2
    if contagens_12[col_menos_frequente] <= 2:
        par_atraso = outras_duas_colunas(col_menos_frequente)
        adicionar_voto(
            par_atraso,
            "atraso_coluna",
            f"{col_menos_frequente} com apenas {contagens_12[col_menos_frequente]}/12 -> {format_cols_nome(par_atraso)}"
        )

    # 4. PRESSÃO DE CONTEXTO CURTO (ÚLTIMAS 6 COLUNAS)
    # Se uma coluna não saiu nas últimas 6, ou se há dominância forte de uma coluna, valida o par oposto
    col_ausente_6 = None
    for c in ("C1", "C2", "C3"):
        if ult_6.count(c) == 0:
            col_ausente_6 = c
            break

    if col_ausente_6:
        par_pressao = outras_duas_colunas(col_ausente_6)
        adicionar_voto(
            par_pressao,
            "pressao_contexto",
            f"{col_ausente_6} ausente nas últimas 6 -> {format_cols_nome(par_pressao)}"
        )

    if not votos_pares:
        return None

    # Escolhe o par de 2 colunas com mais concordância (exige pelo menos 2 fatores a concordar)
    melhor_par = max(votos_pares, key=votos_pares.get)
    max_votos = votos_pares[melhor_par]

    if max_votos < 2:
        return None

    # Determina a estratégia principal registada
    estrategia_registo = "quebra_coluna"
    for r in razoes_por_par[melhor_par]:
        if r.startswith("[alternancia_colunas]"):
            estrategia_registo = "alternancia_colunas"
            break
        if r.startswith("[atraso_coluna]"):
            estrategia_registo = "atraso_coluna"
            break

    return {
        "cols": melhor_par,
        "strategy": estrategia_registo,
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
    results = session["paper_results"]
    total = len(results)

    if total < MIN_PAPER:
        return False

    recent = results[-MIN_RECENTES:]
    wins = sum(results)
    recent_wins = sum(recent)

    lower_bound = wilson_lower_bound(wins, total)
    recent_rate = recent_wins / len(recent)

    return (
        lower_bound > 0.50
        and recent_rate > 0.50
    )


def brain_status(session):
    total = len(session["paper_results"])

    if total < MIN_PAPER:
        return (
            "CALIBRAÇÃO EXPERIMENTAL",
            f"{total}/{MIN_PAPER} simulações concluídas"
        )

    if strategy_validated(session):
        return (
            "FILTRO ESTATÍSTICO APROVADO",
            "Critérios de assertividade cumpridos"
        )

    return (
        "OBSERVAÇÃO",
        "A estratégia ainda não atingiu vantagem estatística exigida"
    )


# =====================================================
# AVALIAÇÃO DE SIMULAÇÃO (PAPEL COM G1, SEM PROTEÇÃO NO 0)
# =====================================================

def evaluate_paper(session, col_result):
    # Fase Gale 1 em papel
    if session.get("pending_paper_g1"):
        pred = session["pending_paper_g1"]
        session["pending_paper_g1"] = None

        if col_result == "Z":
            session["paper_zeros"] += 1

        acertou = (col_result in pred["cols"])
        session["paper_results"].append(acertou)
        session["paper_results"] = session["paper_results"][-1000:]

        strat = pred["strategy"]
        if strat in session["strategy_stats"]:
            session["strategy_stats"][strat]["signals"] += 1
            if acertou:
                session["strategy_stats"][strat]["wins"] += 1
            else:
                session["strategy_stats"][strat]["losses"] += 1
        return

    # Fase Entrada inicial em papel
    pred = session.get("pending_paper")
    if not pred:
        return

    if col_result == "Z":
        session["paper_zeros"] += 1

    session["pending_paper"] = None

    if col_result in pred["cols"]:
        session["paper_results"].append(True)
        session["paper_results"] = session["paper_results"][-1000:]
        strat = pred["strategy"]
        if strat in session["strategy_stats"]:
            session["strategy_stats"][strat]["signals"] += 1
            session["strategy_stats"][strat]["wins"] += 1
    else:
        # Falhou na Entrada -> passa para Gale 1 na simulação
        session["pending_paper_g1"] = pred


# =====================================================
# GESTÃO DAS OPERAÇÕES REAIS (2 COLUNAS, MARTINGALE SPRINT ATÉ G1)
# =====================================================

def close_cycle(session):
    session["active_cols"] = None
    session["gale"] = 0


def process_live_bet(chat_id, session, col_result, raw_label):
    cols = session["active_cols"]
    if cols is None:
        return

    if col_result == "Z":
        session["stats"]["zeros"] += 1

    # ACERTO NUMA DAS 2 COLUNAS ESCOLHIDAS
    if col_result in cols:
        if session["gale"] == 0:
            session["stats"]["wins"] += 1
            nivel = "ENTRADA PRINCIPAL"
        else:
            session["stats"]["wins"] += 1
            session["stats"]["wins_g1"] += 1
            nivel = "GALE 1 (G1)"

        close_cycle(session)

        bot.send_message(
            chat_id,
            "🟢 *GREEN / VITÓRIA CONFIRMADA!* ✨\n\n"
            f"🏆 Resolução: {nivel}\n"
            f"🎯 Resultado: {raw_label} ({col_result})\n"
            f"🧱 Colunas: {format_cols_nome(cols)}\n\n"
            "Ciclo encerrado com sucesso.",
            parse_mode="Markdown"
        )
        return

    # FALHA NA ENTRADA -> SPRINT PARA GALE 1 (DOBRA NAS 2 COLUNAS)
    if session["gale"] == 0:
        session["gale"] = 1
        total_g1 = GALE1_COLUNA * 2

        bot.send_message(
            chat_id,
            "🔴 *LOSS NA ENTRADA PRINCIPAL*\n\n"
            "🔄 **MARTINGALE SPRINT — GALE 1 (G1)** 🚨\n\n"
            f"🧱 Colunas: *{format_cols_nome(cols)}*\n"
            f"💰 Aposta por coluna: {GALE1_COLUNA}€ (Total: {total_g1}€)\n"
            "🚫 Sem proteção no 0 | Sem Gale 2.",
            parse_mode="Markdown"
        )
        return

    # FALHA NO GALE 1 -> PERDA FINAL DO CICLO
    session["stats"]["losses"] += 1
    close_cycle(session)
    losses = session["stats"]["losses"]

    if losses >= LIMITE_LOSSES:
        session["blocked"] = True
        bot.send_message(
            chat_id,
            "🚨 *LIMITE DE PERDAS ATINGIDO!* 🛑\n\n"
            f"🔴 Perdas finais: {losses}/{LIMITE_LOSSES}\n\n"
            "🛑 Sessão bloqueada de imediato.\n"
            "Utiliza /reset para iniciar uma nova sessão.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id,
            "❌ *LOSS FINAL - GALE 1 FALHADO*\n\n"
            f"🔴 Perdas finais: {losses}/{LIMITE_LOSSES}\n\n"
            "O ciclo terminou. A próxima análise será independente.",
            parse_mode="Markdown"
        )


# =====================================================
# GERAR NOVA DECISÃO DE 2 COLUNAS
# =====================================================

def generate_decision(chat_id, session):
    if session["blocked"] or session["active_cols"] is not None:
        return

    if session["pending_paper"] is not None or session.get("pending_paper_g1") is not None:
        return

    candidate = roulette_columns_brain(session["history"])

    if candidate is None:
        session["stats"]["observations"] += 1
        return

    session["pending_paper"] = candidate
    brain_status(session)

    if not strategy_validated(session):
        return

    cols = candidate["cols"]
    session["active_cols"] = cols
    session["gale"] = 0
    session["stats"]["entries"] += 1

    total_entrada = ENTRADA_COLUNA * 2

    bot.send_message(
        chat_id,
        "🧠 *ROULETTE 2 COLUMNS BRAIN*\n\n"
        "📊 FILTRO ESTATÍSTICO APROVADO\n\n"
        f"🧱 Entrar em: *{format_cols_nome(cols)}*\n"
        f"💰 Aposta: {ENTRADA_COLUNA}€ por coluna (Total: {total_entrada}€)\n"
        f"🔄 Gale 1: {GALE1_COLUNA}€ por coluna (Total: {GALE1_COLUNA * 2}€)\n"
        "🚫 Sem proteção no 0 | Até Gale 1\n\n"
        f"🔎 Estratégia: {candidate['strategy']}\n"
        f"💡 Motivo: {candidate['reason']}",
        parse_mode="Markdown"
    )


# =====================================================
# RECEBER UMA NOVA JOGADA
# =====================================================

def receive_result(chat_id, session, col_result, raw_label):
    evaluate_paper(session, col_result)
    process_live_bet(chat_id, session, col_result, raw_label)

    session["history"].append(col_result)
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

    bot.reply_to(
        message,
        "🤖 *BAC BO / ROULETTE 2 COLUMNS BRAIN*\n\n"
        f"Sistema de 2 Colunas (1ª e 2ª / 1ª e 3ª) com Martingale sprint até Gale 1 e calibração de {MIN_PAPER} ciclos!\n\n"
        f"📊 Envia as tuas {JANELA} jogadas iniciais (números 0-36 ou C1/C2/C3).\n\n"
        "Exemplo:\n"
        "`34 5 17 31 3 17 14 0 21 8`\n\n"
        f"💰 Entrada: {ENTRADA_COLUNA}€ x2 ({total_entrada}€) | 🔄 G1: {GALE1_COLUNA}€ x2 ({total_g1}€)\n"
        "🚫 Sem proteção no 0 | Sem Gale 2\n"
        f"🚨 Máximo: {LIMITE_LOSSES} perdas finais\n\n"
        "/stats - Estatísticas detalhadas\n"
        "/status - Estado do cérebro\n"
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
        "4. O robô avalia sempre pares de 2 colunas sem proteção no 0.\n\n"
        "0 = Zero | C1 = 1ª Coluna | C2 = 2ª Coluna | C3 = 3ª Coluna",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["status"])
def status_command(message):
    session = sessions.get(message.chat.id)
    if session is None:
        bot.reply_to(message, "Utiliza /start primeiro.")
        return

    status, detail = brain_status(session)
    ativa_txt = format_cols_nome(session["active_cols"]) if session["active_cols"] else "NÃO"

    bot.reply_to(
        message,
        "🧠 *ESTADO DO ROULETTE 2 COLUMNS BRAIN*\n\n"
        f"📊 Estado: {status}\n"
        f"🔎 {detail}\n"
        f"📜 Histórico: {len(session['history'])} jogadas\n"
        f"🎯 Simulações concluídas: {len(session['paper_results'])}/{MIN_PAPER}\n"
        f"🟢 Zeros simulados: {session['paper_zeros']}\n"
        f"🛡️ Operação ativa: {ativa_txt}\n"
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
        strat_text += f"• *{s_name}*: {s_data['wins']}W / {s_data['losses']}L ({s_rate:.1f}%)\n"

    bot.reply_to(
        message,
        "📊 *RELATÓRIO ROULETTE 2 COLUMNS BRAIN*\n\n"
        "OPERAÇÕES REAIS\n"
        f"🟢 Greens: {st['wins']} (G1: {st['wins_g1']})\n"
        f"🔴 Perdas finais: {st['losses']}/{LIMITE_LOSSES}\n"
        f"🟢 Zeros detetados: {st['zeros']}\n"
        f"🎯 Entradas: {st['entries']}\n"
        f"📈 Taxa de acerto real: {taxa_real:.2f}%\n\n"
        f"SIMULAÇÃO / PAPEL (Alvo: {MIN_PAPER} ciclos)\n"
        f"📊 Total ciclos simulados: {len(paper)}\n"
        f"📈 Taxa simulada global: {taxa_papel:.2f}%\n"
        f"📈 Taxa últimas {MIN_RECENTES}: {taxa_recente:.2f}%\n"
        f"📉 Limite inferior Wilson: {wilson:.2f}%\n\n"
        "DESEMPENHO POR ESTRATÉGIA\n"
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

    tokens = re.findall(r"C[123]|\d+", message.text.upper())
    if not tokens:
        bot.reply_to(
            message,
            "⚠️ Formato inválido.\nUtiliza números de 0 a 36 ou C1, C2, C3."
        )
        return

    parsed = []
    for tk in tokens:
        col = parse_token_to_col(tk)
        if col is None:
            bot.reply_to(
                message,
                f"⚠️ Valor inválido: `{tk}`.\nUsa números de 0 a 36 ou C1, C2, C3.",
                parse_mode="Markdown"
            )
            return
        parsed.append((tk, col))

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

        candidate = roulette_columns_brain(session["history"])
        if candidate:
            session["pending_paper"] = candidate

        bot.reply_to(
            message,
            "🧠 *HISTÓRICO CARREGADO!* 🚀\n\n"
            f"As {JANELA} jogadas foram guardadas.\n"
            "Envia agora **apenas UMA nova jogada** de cada vez.",
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

    raw_label, col_result = parsed[0]
    receive_result(chat_id, session, col_result, raw_label)

    bot.reply_to(
        message,
        f"✅ Jogada `{raw_label}` ({col_result}) registada! Histórico ativo: `{len(session['history'])}` rondas. A analisar...",
        parse_mode="Markdown"
    )


# =====================================================
# INICIALIZAÇÃO DO BOT
# =====================================================

if __name__ == "__main__":
    print("ROULETTE 2 COLUMNS BRAIN ONLINE")

    Thread(
        target=run_web,
        daemon=True
    ).start()

    bot.infinity_polling(
        skip_pending=True,
        timeout=20,
        long_polling_timeout=20
    )
