
import os
import re
from math import sqrt
from threading import Thread

import telebot
from flask import Flask

# =====================================================
# BAC BO - ULTIMATE BRAIN
# Motor experimental + Telegram + Flask
# =====================================================

TOKEN = os.getenv(
    "BOT_TOKEN",
    "8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0"
)

if not TOKEN or TOKEN == "COLOCA_AQUI_O_TEU_TOKEN_NOVO":
    raise ValueError("Configura o teu novo token BOT_TOKEN.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# CONFIGURAÇÕES
ENTRADA = 3
GALE1 = 6
PROTECAO_T = 1

JANELA = 10
LIMITE_LOSSES = 2

MIN_PAPER = 100
MIN_RECENTES = 50

# Sessões em memória
sessions = {}


# =====================================================
# SERVIDOR WEB
# =====================================================

@app.route("/")
def home():
    return "BAC BO ULTIMATE BRAIN - ONLINE"


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
        "history": [],
        "awaiting_seed": True,

        "active_target": None,
        "gale": 0,
        "blocked": False,

        # Previsão experimental pendente
        "pending_paper": None,

        # Resultados da simulação em tempo real
        "paper_results": [],
        "paper_ties": 0,

        # Estatísticas das operações
        "stats": {
            "wins": 0,
            "wins_g1": 0,
            "losses": 0,
            "ties": 0,
            "entries": 0,
            "observations": 0
        }
    }


# =====================================================
# CÉREBRO - ANÁLISE DAS ÚLTIMAS 10 JOGADAS
# =====================================================

def ultimate_brain(history):

    if len(history) < JANELA:
        return None

    window = history[-JANELA:]

    colors = [
        x for x in window
        if x in ("A", "V")
    ]

    if len(colors) < 7:
        return None

    total_a = colors.count("A")
    total_v = colors.count("V")

    # Detetar sequência consecutiva
    streak = 1

    for i in range(len(colors) - 1, 0, -1):
        if colors[i] == colors[i - 1]:
            streak += 1
        else:
            break

    last_color = colors[-1]

    # REGRA 1:
    # Sequência prolongada: testar hipótese de inversão
    if streak >= 5:
        return {
            "color": "V" if last_color == "A" else "A",
            "reason": f"Sequência de {streak} resultados iguais",
            "pattern": "streak_reversal"
        }

    # REGRA 2:
    # Desequilíbrio muito elevado: testar correção
    if total_a >= 8:
        return {
            "color": "V",
            "reason": f"{total_a} AZUIS nas últimas 10",
            "pattern": "imbalance_reversal"
        }

    if total_v >= 8:
        return {
            "color": "A",
            "reason": f"{total_v} VERMELHOS nas últimas 10",
            "pattern": "imbalance_reversal"
        }

    # Sem hipótese suficientemente definida
    return None


# =====================================================
# TESTE ESTATÍSTICO
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

    lower_bound = wilson_lower_bound(
        wins,
        total
    )

    recent_rate = recent_wins / len(recent)

    return (
        lower_bound > 0.50
        and recent_rate > 0.50
    )


# =====================================================
# ESTADO DO CÉREBRO
# =====================================================

def brain_status(session):

    total = len(session["paper_results"])

    if total < MIN_PAPER:
        return (
            "CALIBRAÇÃO EXPERIMENTAL",
            f"{total}/{MIN_PAPER} previsões simuladas"
        )

    if strategy_validated(session):
        return (
            "FILTRO ESTATÍSTICO APROVADO",
            "Critérios experimentais cumpridos"
        )

    return (
        "OBSERVAÇÃO",
        "A estratégia ainda não demonstrou vantagem"
    )


# =====================================================
# PROCESSAMENTO DE PREVISÕES SIMULADAS
# =====================================================

def evaluate_paper(session, real_result):

    prediction = session["pending_paper"]

    if prediction is None:
        return

    if real_result == "T":
        session["paper_ties"] += 1

    else:
        correct = prediction["color"] == real_result

        session["paper_results"].append(correct)

        # Manter um histórico limitado
        session["paper_results"] = (
            session["paper_results"][-1000:]
        )

    session["pending_paper"] = None


# =====================================================
# GESTÃO DAS OPERAÇÕES
# =====================================================

def close_cycle(session):
    session["active_target"] = None
    session["gale"] = 0


def process_live_bet(chat_id, session, result):

    target = session["active_target"]

    if target is None:
        return

    # EMPATE
    if result == "T":

        session["stats"]["ties"] += 1

        close_cycle(session)

        bot.send_message(
            chat_id,
            "🟡 *RESULTADO EMPATE (T)*\n\n"
            "Ciclo encerrado.\n"
            "Empate registado separadamente.\n"
            "A liquidação financeira depende das "
            "regras da mesa.\n\n"
            "O cérebro vai analisar novamente.",
            parse_mode="Markdown"
        )

        return

    # ACERTO
    if result == target:

        if session["gale"] == 0:
            session["stats"]["wins"] += 1
            level = "ENTRADA PRINCIPAL"
        else:
            session["stats"]["wins"] += 1
            session["stats"]["wins_g1"] += 1
            level = "GALE 1"

        close_cycle(session)

        bot.send_message(
            chat_id,
            "🟢 *RESULTADO CORRETO!*\n\n"
            f"🏆 Resolução: {level}\n"
            f"🎯 Resultado: {result}\n\n"
            "Ciclo encerrado.\n"
            "A aguardar nova análise.",
            parse_mode="Markdown"
        )

        return

    # FALHA DA ENTRADA PRINCIPAL
    if session["gale"] == 0:

        session["gale"] = 1

        cor_nome = (
            "AZUL 🔵" if target == "A"
            else "VERMELHO 🔴"
        )

        bot.send_message(
            chat_id,
            "🔴 *LOSS NA ENTRADA PRINCIPAL*\n\n"
            "🚨 ÚLTIMO NÍVEL: GALE 1\n\n"
            f"👉 Direção: {cor_nome}\n"
            f"💰 Gale 1: {GALE1}€\n"
            f"🟡 Proteção T: {PROTECAO_T}€\n\n"
            "Não existe Gale 2.",
            parse_mode="Markdown"
        )

        return

    # FALHA FINAL
    session["stats"]["losses"] += 1

    close_cycle(session)

    losses = session["stats"]["losses"]

    if losses >= LIMITE_LOSSES:

        session["blocked"] = True

        bot.send_message(
            chat_id,
            "🚨 *LIMITE DE PERDAS ATINGIDO!*\n\n"
            f"🔴 Losses: {losses}/{LIMITE_LOSSES}\n\n"
            "🛑 Sessão bloqueada.\n"
            "Não serão autorizadas novas entradas.\n"
            "Utiliza /reset para iniciar uma nova sessão.",
            parse_mode="Markdown"
        )

    else:

        bot.send_message(
            chat_id,
            "❌ *LOSS FINAL - GALE 1 FALHADO*\n\n"
            f"🔴 Losses: {losses}/{LIMITE_LOSSES}\n\n"
            "O ciclo terminou.\n"
            "A próxima análise será independente.",
            parse_mode="Markdown"
        )


# =====================================================
# GERAR NOVA DECISÃO
# =====================================================

def generate_decision(chat_id, session):

    if session["blocked"]:
        return

    if session["active_target"] is not None:
        return

    candidate = ultimate_brain(
        session["history"]
    )

    if candidate is None:

        session["stats"]["observations"] += 1

        bot.send_message(
            chat_id,
            "🧠 *ULTIMATE BRAIN*\n\n"
            "👁️ MODO OBSERVAÇÃO\n\n"
            "Não foi encontrado um padrão selecionável.\n"
            "O cérebro não vai forçar uma entrada.\n\n"
            "A aguardar nova jogada.",
            parse_mode="Markdown"
        )

        return

    # Registar hipótese para avaliação futura
    session["pending_paper"] = candidate

    status, detail = brain_status(session)

    # Sem validação: apenas observação
    if not strategy_validated(session):

        bot.send_message(
            chat_id,
            "🧠 *ULTIMATE BRAIN - CALIBRAÇÃO*\n\n"
            f"🔎 Hipótese: {candidate['reason']}\n"
            f"🎯 Direção experimental: {candidate['color']}\n\n"
            f"📊 Estado: {status}\n"
            f"📈 {detail}\n\n"
            "🛡️ Ainda não existe autorização "
            "para entrada real.\n"
            "A previsão será avaliada em modo simulado.",
            parse_mode="Markdown"
        )

        return

    # Critérios experimentais cumpridos
    session["active_target"] = candidate["color"]
    session["gale"] = 0
    session["stats"]["entries"] += 1

    cor_nome = (
        "AZUL 🔵" if candidate["color"] == "A"
        else "VERMELHO 🔴"
    )

    bot.send_message(
        chat_id,
        "🧠 *ULTIMATE BRAIN*\n\n"
        "📊 FILTRO EXPERIMENTAL APROVADO\n\n"
        f"🎯 Direção: {cor_nome}\n"
        f"💰 Entrada: {ENTRADA}€\n"
        f"🟡 Proteção T: {PROTECAO_T}€\n\n"
        f"🔎 Motivo: {candidate['reason']}\n\n"
        "⚠️ Aprovação estatística histórica não "
        "garante vantagem futura.\n"
        "A entrada continua a ser uma decisão "
        "de risco.",
        parse_mode="Markdown"
    )


# =====================================================
# RECEBER UMA NOVA JOGADA
# =====================================================

def receive_result(chat_id, session, result):

    # Primeiro avalia a previsão anterior
    evaluate_paper(session, result)

    # Depois trata uma eventual operação ativa
    process_live_bet(
        chat_id,
        session,
        result
    )

    # Atualizar histórico
    session["history"].append(result)

    session["history"] = (
        session["history"][-250:]
    )

    # Analisar novamente a janela atualizada
    if not session["blocked"]:
        generate_decision(chat_id, session)


# =====================================================
# COMANDO START
# =====================================================

@bot.message_handler(commands=["start"])
def start(message):

    sessions[message.chat.id] = nova_sessao()

    bot.reply_to(
        message,
        "🤖 *BAC BO - ULTIMATE BRAIN*\n\n"
        "Sistema iniciado!\n\n"
        "📊 Envia as tuas últimas 10 jogadas.\n\n"
        "Exemplo:\n"
        "`A V A A V T V A V V`\n\n"
        "🔵 A = Azul\n"
        "🔴 V = Vermelho\n"
        "🟡 T = Empate\n\n"
        "💰 Entrada: 3€\n"
        "🔄 G1: 6€\n"
        "🛡️ Proteção T: 1€\n"
        "🚨 Máximo: 2 perdas\n\n"
        "/stats - Estatísticas\n"
        "/status - Estado do cérebro\n"
        "/reset - Reiniciar sessão\n"
        "/ajuda - Ajuda",
        parse_mode="Markdown"
    )


# =====================================================
# COMANDO AJUDA
# =====================================================

@bot.message_handler(commands=["ajuda"])
def help_command(message):

    bot.reply_to(
        message,
        "📖 *COMO UTILIZAR*\n\n"
        "1. Utiliza /start.\n"
        "2. Envia exatamente 10 jogadas iniciais.\n"
        "3. Depois envia apenas uma jogada de cada vez.\n"
        "4. O cérebro atualiza a análise após cada resultado.\n\n"
        "Nunca envies várias jogadas futuras de uma só vez.\n\n"
        "A = Azul | V = Vermelho | T = Empate",
        parse_mode="Markdown"
    )


# =====================================================
# COMANDO STATUS
# =====================================================

@bot.message_handler(commands=["status"])
def status_command(message):

    session = sessions.get(message.chat.id)

    if session is None:
        bot.reply_to(message, "Utiliza /start primeiro.")
        return

    status, detail = brain_status(session)

    bot.reply_to(
        message,
        "🧠 *ESTADO DO ULTIMATE BRAIN*\n\n"
        f"📊 Estado: {status}\n"
        f"🔎 {detail}\n"
        f"📜 Histórico: {len(session['history'])} jogadas\n"
        f"🎯 Previsões simuladas: "
        f"{len(session['paper_results'])}\n"
        f"🟡 Empates simulados: {session['paper_ties']}\n"
        f"🛡️ Operação ativa: "
        f"{'SIM' if session['active_target'] else 'NÃO'}\n"
        f"🚨 Bloqueado: "
        f"{'SIM' if session['blocked'] else 'NÃO'}",
        parse_mode="Markdown"
    )


# =====================================================
# COMANDO STATS
# =====================================================

@bot.message_handler(commands=["stats"])
def stats_command(message):

    session = sessions.get(message.chat.id)

    if session is None:
        bot.reply_to(message, "Utiliza /start primeiro.")
        return

    st = session["stats"]

    resolved = st["wins"] + st["losses"]

    rate = (
        st["wins"] / resolved * 100
        if resolved else 0
    )

    paper = session["paper_results"]

    paper_rate = (
        sum(paper) / len(paper) * 100
        if paper else 0
    )

    lower = (
        wilson_lower_bound(sum(paper), len(paper)) * 100
        if paper else 0
    )

    bot.reply_to(
        message,
        "📊 *RELATÓRIO ULTIMATE BRAIN*\n\n"
        "REAL / OPERAÇÕES\n"
        f"🟢 Greens: {st['wins']}\n"
        f"🏆 Greens em G1: {st['wins_g1']}\n"
        f"🔴 Losses finais: {st['losses']}\n"
        f"🟡 Empates: {st['ties']}\n"
        f"🎯 Entradas: {st['entries']}\n"
        f"📈 Taxa de acerto: {rate:.2f}%\n\n"
        "SIMULAÇÃO / PAPEL\n"
        f"📊 Previsões avaliadas: {len(paper)}\n"
        f"🟢 Acertos: {sum(paper)}\n"
        f"🔴 Erros: {len(paper) - sum(paper)}\n"
        f"🟡 Empates simulados: {session['paper_ties']}\n"
        f"📈 Taxa simulada: {paper_rate:.2f}%\n"
        f"📉 Limite inferior Wilson: {lower:.2f}%\n\n"
        "Nota: taxas de acerto não representam lucro.\n"
        "Empates são excluídos da taxa de acerto.",
        parse_mode="Markdown"
    )


# =====================================================
# COMANDO RESET
# =====================================================

@bot.message_handler(commands=["reset"])
def reset_command(message):

    sessions[message.chat.id] = nova_sessao()

    bot.reply_to(
        message,
        "🔄 Sessão reiniciada!\n\n"
        "Envia novamente as últimas 10 jogadas.\n"
        "As estatísticas anteriores foram reiniciadas."
    )


# =====================================================
# RECEBER RESULTADOS
# =====================================================

@bot.message_handler(
    func=lambda m: True,
    content_types=["text"]
)
def handle_results(message):

    chat_id = message.chat.id
    session = sessions.get(chat_id)

    if session is None:
        bot.reply_to(
            message,
            "Utiliza /start para iniciar o cérebro."
        )
        return

    raw = message.text.upper()

    cleaned = re.sub(
        r"[\s,;|]+",
        "",
        raw
    )

    if not cleaned or any(
        c not in "AVT" for c in cleaned
    ):
        bot.reply_to(
            message,
            "⚠️ Formato inválido.\n"
            "Utiliza apenas A, V ou T."
        )
        return

    # BLOQUEIO DE SESSÃO
    if session["blocked"]:
        bot.reply_to(
            message,
            "🛑 Sessão bloqueada.\n"
            "Utiliza /reset para iniciar outra."
        )
        return

    # PRIMEIRO ENVIO: HISTÓRICO INICIAL
    if session["awaiting_seed"]:

        if len(cleaned) != JANELA:
            bot.reply_to(
                message,
                "⚠️ Preciso de exatamente 10 jogadas iniciais.\n"
                "Exemplo: AVAVTVAVVV"
            )
            return

        session["history"] = list(cleaned)
        session["awaiting_seed"] = False

        candidate = ultimate_brain(
            session["history"]
        )

        session["pending_paper"] = candidate

        bot.reply_to(
            message,
            "🧠 *HISTÓRICO CARREGADO!*\n\n"
            "As 10 jogadas foram guardadas.\n"
            "Nenhuma foi tratada como aposta.\n\n"
            "📊 O cérebro está em calibração.\n"
            "A partir de agora envia apenas UMA "
            "nova jogada de cada vez.\n\n"
            "Utiliza /status para acompanhar.",
            parse_mode="Markdown"
        )

        return

    # DEPOIS DO HISTÓRICO: UMA JOGADA DE CADA VEZ
    if len(cleaned) != 1:

        bot.reply_to(
            message,
            "⚠️ Depois das 10 jogadas iniciais, "
            "envia apenas um resultado por mensagem.\n\n"
            "Exemplo: A"
        )
        return

    receive_result(
        chat_id,
        session,
        cleaned
    )


# =====================================================
# INICIAR
# =====================================================

if __name__ == "__main__":

    print("BAC BO ULTIMATE BRAIN ONLINE")

    Thread(
        target=run_web,
        daemon=True
    ).start()

    bot.infinity_polling(
        skip_pending=True,
        timeout=20,
        long_polling_timeout=20
    )
