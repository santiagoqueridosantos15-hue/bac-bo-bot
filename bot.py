import os
import re
from math import sqrt
from threading import Thread

import telebot
from flask import Flask

# =====================================================
# BAC BO - MULTI STRATEGY BRAIN
# Telegram + Flask + Render
# =====================================================

TOKEN = os.getenv("8922303337:AAGiqzCVesRtMgy1mIR1vK3hF7SW9wsONM0")
if not TOKEN:
    raise ValueError("Falta configurar BOT_TOKEN nas Environment Variables do Render.")

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# CONFIGURAÇÕES MANTIDAS
ENTRADA = 3
GALE1 = 6
PROTECAO_T = 1
JANELA = 10
LIMITE_LOSSES = 2
MIN_PAPER = 100
MIN_RECENTES = 50

# Só estas estratégias podem emitir uma direção.
DIRECTIONAL_STRATEGIES = (
    "quebra_sequencia",
    "alternancia",
    "reversao_desequilibrio",
)
STRATEGY_NAMES = {
    "quebra_sequencia": "Quebra de sequência",
    "alternancia": "Alternância",
    "reversao_desequilibrio": "Reversão após desequilíbrio",
    "maioria_recente": "Maioria recente (filtro)",
}

sessions = {}


# =====================================================
# SERVIDOR WEB
# =====================================================

@app.route("/")
def home():
    return "BAC BO MULTI STRATEGY BRAIN - ONLINE", 200


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)


# =====================================================
# SESSÃO
# =====================================================

def nova_sessao():
    return {
        "history": [],
        "awaiting_seed": True,
        "active_target": None,
        "gale": 0,
        "blocked": False,
        "pending_paper": None,
        "paper_results": [],
        "paper_ties": 0,
        "strategy_stats": {
            key: {"signals": 0, "wins": 0, "losses": 0}
            for key in STRATEGY_NAMES
        },
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
# FERRAMENTAS DO CÉREBRO
# =====================================================

def color_windows(history):
    """Retira empates para estudar apenas a sequência Azul/Vermelho."""
    colors = [x for x in history if x in ("A", "V")]
    return {
        5: colors[-5:],
        10: colors[-10:],
        20: colors[-20:],
        "all": colors
    }


def majority_of(values):
    if not values:
        return None
    a = values.count("A")
    v = values.count("V")
    if a == v:
        return None
    return "A" if a > v else "V"


def trailing_run(values):
    if not values:
        return 0, None
    color = values[-1]
    count = 0
    for value in reversed(values):
        if value != color:
            break
        count += 1
    return count, color


# =====================================================
# QUATRO ESTRATÉGIAS
# =====================================================

def strategy_break_of_sequence(colors):
    """
    Só considera uma sequência que já foi quebrada.
    Exemplo: A-A-A-V pode sinalizar V.
    Nunca aposta contra uma sequência que ainda está ativa.
    """
    if len(colors) < 5:
        return None

    last_run, last_color = trailing_run(colors)
    if last_run > 2:
        return None

    previous = colors[:-last_run]
    previous_run, previous_color = trailing_run(previous)

    if previous_run >= 3 and previous_color != last_color:
        return {
            "color": last_color,
            "reason": (
                f"sequência anterior de {previous_run} "
                f"{previous_color} já foi quebrada por {last_color}"
            )
        }
    return None


def strategy_alternation(colors):
    """Procura alternância real nas quatro últimas cores."""
    if len(colors) < 4:
        return None

    last_four = colors[-4:]
    alternating = all(
        last_four[i] != last_four[i - 1]
        for i in range(1, len(last_four))
    )
    if not alternating:
        return None

    next_color = "A" if last_four[-1] == "V" else "V"
    return {
        "color": next_color,
        "reason": "as últimas 4 cores formam alternância"
    }


def strategy_recent_majority(windows):
    """
    É apenas um filtro de contexto: não escolhe Azul nem Vermelho.
    Não presume continuação nem reversão da maioria.
    """
    majorities = [
        majority_of(windows[size])
        for size in (5, 10, 20)
        if len(windows[size]) >= size
    ]
    if len(majorities) == 3 and all(x == majorities[0] for x in majorities):
        return (
            f"maioria consistente nas janelas 5/10/20: {majorities[0]}"
        )
    return "maioria sem alinhamento consistente; sem indicação direcional"


def strategy_imbalance_reversal(windows):
    """
    Só considera reversão após desequilíbrio quando já há confirmação
    de mudança: as duas últimas cores são do lado minoritário.
    Não entra apenas porque uma cor saiu muitas vezes.
    """
    values = windows[10]
    if len(values) < 10:
        return None

    a = values.count("A")
    v = values.count("V")
    if max(a, v) < 7 or a == v:
        return None

    dominant = "A" if a > v else "V"
    minority = "V" if dominant == "A" else "A"

    if values[-1] == minority and values[-2] == minority:
        return {
            "color": minority,
            "reason": (
                f"desequilíbrio recente ({max(a, v)}/10) "
                f"seguido de duas ocorrências de {minority}"
            )
        }
    return None


# =====================================================
# CÉREBRO PRINCIPAL - CONSENSO
# =====================================================

def ultimate_brain(history):
    if len(history) < JANELA:
        return None

    windows = color_windows(history)
    colors = windows["all"]
    if len(colors) < 7:
        return None

    signals = {}
    for key, function in (
        ("quebra_sequencia", strategy_break_of_sequence),
        ("alternancia", strategy_alternation),
        ("reversao_desequilibrio", strategy_imbalance_reversal),
    ):
        signal = function(colors) if key != "reversao_desequilibrio" else function(windows)
        if signal:
            signals[key] = signal

    majority_context = strategy_recent_majority(windows)

    votes = {"A": [], "V": []}
    for key, signal in signals.items():
        votes[signal["color"]].append(key)

    # Exige pelo menos duas estratégias independentes na mesma direção.
    # Se houver votos divididos, não há entrada.
    if len(votes["A"]) >= 2 and not votes["V"]:
        chosen = "A"
        agreeing = votes["A"]
    elif len(votes["V"]) >= 2 and not votes["A"]:
        chosen = "V"
        agreeing = votes["V"]
    else:
        return None

    reasons = [
        f"{STRATEGY_NAMES[key]}: {signals[key]['reason']}"
        for key in agreeing
    ]

    return {
        "color": chosen,
        "reason": " | ".join(reasons),
        "pattern": "+".join(agreeing),
        "strategies": agreeing,
        "majority_context": majority_context,
    }


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
    lower_bound = wilson_lower_bound(sum(results), total)
    recent_rate = sum(recent) / len(recent)
    return lower_bound > 0.50 and recent_rate > 0.50


def brain_status(session):
    total = len(session["paper_results"])
    if total < MIN_PAPER:
        return (
            "CALIBRAÇÃO EXPERIMENTAL",
            f"{total}/{MIN_PAPER} ciclos simulados concluídos"
        )
    if strategy_validated(session):
        return (
            "FILTRO ESTATÍSTICO APROVADO",
            "Critérios experimentais cumpridos"
        )
    return (
        "OBSERVAÇÃO",
        "A simulação ainda não demonstrou os critérios definidos"
    )


# =====================================================
# SIMULAÇÃO - ENTRADA + GALE 1
# =====================================================

def evaluate_paper(session, real_result):
    prediction = session["pending_paper"]
    if prediction is None:
        return

    target = prediction["color"]
    gale = prediction.get("gale", 0)

    if real_result == "T":
        session["paper_ties"] += 1
        session["paper_results"].append(True)
        outcome = "win"
        session["pending_paper"] = None
    elif real_result == target:
        session["paper_results"].append(True)
        outcome = "win"
        session["pending_paper"] = None
    elif gale == 0:
        prediction["gale"] = 1
        return
    else:
        session["paper_results"].append(False)
        outcome = "loss"
        session["pending_paper"] = None

    for key in prediction.get("strategies", []):
        if outcome == "win":
            session["strategy_stats"][key]["wins"] += 1
        else:
            session["strategy_stats"][key]["losses"] += 1

    session["paper_results"] = session["paper_results"][-1000:]


# =====================================================
# GESTÃO DAS OPERAÇÕES REAIS
# =====================================================

def close_cycle(session):
    session["active_target"] = None
    session["gale"] = 0


def process_live_bet(chat_id, session, result):
    target = session["active_target"]
    if target is None:
        return

    gale = session["gale"]
    st = session["stats"]

    if result == "T":
        st["ties"] += 1
        st["wins"] += 1
        if gale == 1:
            st["wins_g1"] += 1
            level = "GALE 1 - EMPATE GREEN"
        else:
            level = "ENTRADA PRINCIPAL - EMPATE GREEN"
        close_cycle(session)
        bot.send_message(
            chat_id,
            "🟢 *GREEN - EMPATE!*\n\n"
            f"🏆 Resolução: {level}\n"
            "🟡 Resultado: T\n"
            "✅ Empate contabilizado como GREEN.\n\n"
            "Ciclo encerrado.",
            parse_mode="Markdown"
        )
        return

    if result == target:
        st["wins"] += 1
        if gale == 1:
            st["wins_g1"] += 1
            level = "GALE 1"
        else:
            level = "ENTRADA PRINCIPAL"
        close_cycle(session)
        bot.send_message(
            chat_id,
            "🟢 *GREEN CONFIRMADO!*\n\n"
            f"🏆 Resolução: {level}\n"
            f"🎯 Resultado: {result}\n\n"
            "Ciclo encerrado.",
            parse_mode="Markdown"
        )
        return

    if gale == 0:
        session["gale"] = 1
        cor_nome = "AZUL 🔵" if target == "A" else "VERMELHO 🔴"
        bot.send_message(
            chat_id,
            "🔴 *ENTRADA PRINCIPAL FALHADA*\n\n"
            "⚠️ Ainda NÃO é LOSS FINAL!\n\n"
            "🚨 Ativar GALE 1\n"
            f"👉 Direção: {cor_nome}\n"
            f"💰 Gale 1: {GALE1}€\n"
            f"🟡 Proteção T indicada: {PROTECAO_T}€\n\n"
            "Não existe Gale 2.",
            parse_mode="Markdown"
        )
        return

    st["losses"] += 1
    close_cycle(session)
    losses = st["losses"]

    if losses >= LIMITE_LOSSES:
        session["blocked"] = True
        bot.send_message(
            chat_id,
            "🚨 *LIMITE DE LOSSES ATINGIDO!*\n\n"
            f"🔴 Losses finais: {losses}/{LIMITE_LOSSES}\n\n"
            "🛑 Sessão bloqueada.\n"
            "Utiliza /reset para começar outra sessão.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id,
            "❌ *LOSS FINAL - GALE 1 FALHADO*\n\n"
            f"🔴 Losses finais: {losses}/{LIMITE_LOSSES}\n\n"
            "Os dois níveis falharam.\n"
            "O ciclo terminou.",
            parse_mode="Markdown"
        )


# =====================================================
# GERAR DECISÃO
# =====================================================

def generate_decision(chat_id, session):
    if session["blocked"] or session["active_target"] is not None:
        return

    candidate = ultimate_brain(session["history"])
    if candidate is None:
        session["stats"]["observations"] += 1
        bot.send_message(
            chat_id,
            "🧠 *MULTI STRATEGY BRAIN*\n\n"
            "👁️ MODO OBSERVAÇÃO\n"
            "Não existem duas estratégias concordantes.\n"
            "O cérebro não vai forçar uma entrada.\n\n"
            "A aguardar nova jogada.",
            parse_mode="Markdown"
        )
        return

    # Uma previsão simulada tem de terminar (incluindo eventual G1)
    # antes de começar outro ciclo ou abrir uma operação real.
    created_paper_now = False
    if session["pending_paper"] is None:
        session["pending_paper"] = {
            "color": candidate["color"],
            "reason": candidate["reason"],
            "pattern": candidate["pattern"],
            "strategies": list(candidate["strategies"]),
            "gale": 0
        }
        created_paper_now = True
        for key in candidate["strategies"]:
            session["strategy_stats"][key]["signals"] += 1
    elif not created_paper_now:
        bot.send_message(
            chat_id,
            "🧠 *MULTI STRATEGY BRAIN*\\n\\n"
            "A previsão simulada anterior ainda está pendente "
            "(entrada ou Gale 1).\\n"
            "Vou esperar que esse ciclo termine antes de avaliar "
            "uma nova oportunidade.",
            parse_mode="Markdown"
        )
        return

    status, detail = brain_status(session)

    if not strategy_validated(session):
        bot.send_message(
            chat_id,
            "🧠 *MULTI STRATEGY BRAIN - CALIBRAÇÃO*\n\n"
            f"🔎 Estratégias concordantes: {', '.join(STRATEGY_NAMES[k] for k in candidate['strategies'])}\n"
            f"🎯 Direção experimental: {candidate['color']}\n"
            f"📚 Contexto de maioria: {candidate['majority_context']}\n\n"
            f"📊 Estado: {status}\n"
            f"📈 {detail}\n\n"
            "🛡️ Ainda não existe autorização para entrada real.\n"
            "A previsão será avaliada em simulação.",
            parse_mode="Markdown"
        )
        return

    session["active_target"] = candidate["color"]
    session["gale"] = 0
    session["stats"]["entries"] += 1
    cor_nome = "AZUL 🔵" if candidate["color"] == "A" else "VERMELHO 🔴"

    bot.send_message(
        chat_id,
        "🧠 *MULTI STRATEGY BRAIN*\n\n"
        "📊 FILTRO EXPERIMENTAL APROVADO\n\n"
        f"🎯 Direção: {cor_nome}\n"
        f"💰 Entrada: {ENTRADA}€\n"
        f"🟡 Proteção T indicada: {PROTECAO_T}€\n\n"
        f"🔎 Motivo: {candidate['reason']}\n"
        f"📚 Maioria recente: {candidate['majority_context']}\n\n"
        "⚠️ Resultados históricos não garantem vantagem futura.",
        parse_mode="Markdown"
    )


# =====================================================
# RECEBER RESULTADO
# =====================================================

def receive_result(chat_id, session, result):
    evaluate_paper(session, result)
    process_live_bet(chat_id, session, result)

    session["history"].append(result)
    session["history"] = session["history"][-250:]

    if not session["blocked"]:
        generate_decision(chat_id, session)


# =====================================================
# COMANDOS TELEGRAM
# =====================================================

@bot.message_handler(commands=["start"])
def start(message):
    sessions[message.chat.id] = nova_sessao()
    bot.reply_to(
        message,
        "🤖 *BAC BO - MULTI STRATEGY BRAIN*\n\n"
        "Sistema iniciado!\n\n"
        "Envia as últimas 10 jogadas.\n"
        "Exemplo: `A V A A V T V A V V`\n\n"
        "🔵 A = Azul\n🔴 V = Vermelho\n🟡 T = Empate\n\n"
        "💰 Entrada: 3€\n🔄 G1: 6€\n"
        "🛡️ Proteção T indicada: 1€\n"
        "🚨 Máximo: 2 losses finais\n\n"
        "/stats - Estatísticas\n/status - Estado\n"
        "/reset - Reiniciar sessão\n/ajuda - Ajuda",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["ajuda"])
def help_command(message):
    bot.reply_to(
        message,
        "📖 *COMO UTILIZAR*\n\n"
        "1. Utiliza /start.\n"
        "2. Envia exatamente 10 jogadas iniciais.\n"
        "3. Depois envia apenas uma jogada de cada vez.\n"
        "4. O cérebro analisa após cada resultado.\n\n"
        "Estratégias: quebra de sequência, alternância, "
        "maioria recente como filtro e reversão após desequilíbrio.\n"
        "Não segue tendências nem força entradas.\n\n"
        "A = Azul | V = Vermelho | T = Empate",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["status"])
def status_command(message):
    session = sessions.get(message.chat.id)
    if session is None:
        bot.reply_to(message, "Utiliza /start primeiro.")
        return

    status, detail = brain_status(session)
    pending = session["pending_paper"]
    active = session["active_target"]

    bot.reply_to(
        message,
        "🧠 *ESTADO DO MULTI STRATEGY BRAIN*\n\n"
        f"📊 Estado: {status}\n"
        f"🔎 {detail}\n"
        f"📜 Histórico: {len(session['history'])} jogadas\n"
        f"🎯 Ciclos simulados: {len(session['paper_results'])}\n"
        f"🟡 Empates simulados: {session['paper_ties']}\n"
        f"🧪 Previsão simulada pendente: {'SIM' if pending else 'NÃO'}\n"
        f"💰 Operação real ativa: {'SIM' if active else 'NÃO'}\n"
        f"🔄 Nível: {'GALE 1' if session['gale'] == 1 else 'ENTRADA PRINCIPAL'}\n"
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
    resolved = st["wins"] + st["losses"]
    rate = st["wins"] / resolved * 100 if resolved else 0

    paper = session["paper_results"]
    paper_wins = sum(paper)
    paper_rate = paper_wins / len(paper) * 100 if paper else 0
    lower = wilson_lower_bound(paper_wins, len(paper)) * 100 if paper else 0

    strategy_lines = []
    for key, name in STRATEGY_NAMES.items():
        data = session["strategy_stats"][key]
        count = data["wins"] + data["losses"]
        pct = data["wins"] / count * 100 if count else 0
        strategy_lines.append(
            f"• {name}: {data['signals']} sinais | "
            f"{data['wins']} GREEN | {data['losses']} LOSS | {pct:.1f}%"
        )

    bot.reply_to(
        message,
        "📊 *RELATÓRIO MULTI STRATEGY BRAIN*\n\n"
        "REAL / OPERAÇÕES\n"
        f"🟢 Greens (inclui empates): {st['wins']}\n"
        f"🏆 Greens em G1: {st['wins_g1']}\n"
        f"🔴 Losses finais: {st['losses']}\n"
        f"🟡 Empates: {st['ties']}\n"
        f"🎯 Entradas: {st['entries']}\n"
        f"📈 Taxa de GREEN: {rate:.2f}%\n\n"
        "SIMULAÇÃO / PAPEL\n"
        f"📊 Ciclos concluídos: {len(paper)}\n"
        f"🟢 Greens: {paper_wins}\n"
        f"🔴 Losses finais: {len(paper) - paper_wins}\n"
        f"🟡 Empates: {session['paper_ties']}\n"
        f"📈 Taxa GREEN: {paper_rate:.2f}%\n"
        f"📉 Limite inferior Wilson: {lower:.2f}%\n\n"
        "ESTRATÉGIAS (resultados dos ciclos em que participaram)\n"
        + "\n".join(strategy_lines)
        + "\n\nNota: a maioria recente é apenas um filtro de contexto, "
        "não escolhe uma direção.\n"
        "GREEN não significa necessariamente lucro. A proteção T de 1€ "
        "é apenas indicada, não é executada pelo bot.",
        parse_mode="Markdown"
    )


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

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_results(message):
    chat_id = message.chat.id
    session = sessions.get(chat_id)

    if session is None:
        bot.reply_to(message, "Utiliza /start para iniciar o cérebro.")
        return

    raw = message.text.upper()
    cleaned = re.sub(r"[\s,;|]+", "", raw)

    if not cleaned or any(c not in "AVT" for c in cleaned):
        bot.reply_to(message, "⚠️ Formato inválido. Utiliza apenas A, V ou T.")
        return

    if session["blocked"]:
        bot.reply_to(message, "🛑 Sessão bloqueada. Utiliza /reset para iniciar outra.")
        return

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
        bot.reply_to(
            message,
            "🧠 *HISTÓRICO CARREGADO!*\n\n"
            "As 10 jogadas foram guardadas; nenhuma foi tratada como aposta.\n"
            "A partir de agora envia apenas UMA jogada por mensagem.",
            parse_mode="Markdown"
        )
        return

    if len(cleaned) != 1:
        bot.reply_to(
            message,
            "⚠️ Depois das 10 jogadas iniciais, envia apenas um resultado por mensagem.\n"
            "Exemplo: A"
        )
        return

    receive_result(chat_id, session, cleaned)


# =====================================================
# ARRANQUE - UMA ÚNICA INSTÂNCIA DE POLLING
# =====================================================

if __name__ == "__main__":
    print("BAC BO MULTI STRATEGY BRAIN ONLINE")
    Thread(target=run_web, daemon=True).start()
    bot.remove_webhook()
    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30
    )
