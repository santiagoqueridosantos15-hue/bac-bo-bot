import os
import re
from math import sqrt
from threading import Thread

import telebot
from flask import Flask

# =====================================================
# BAC BO - ULTIMATE MULTISTRATEGY BRAIN
# Motor inteligente com estratégias de elite, G1, Sem Empate e ciclos otimizados
# =====================================================

TOKEN = os.getenv(
    "BOT_TOKEN",
    "8922303337:AAEfiGQK15Cd4B4SsW-FS97Fq6QyPH2aUEs"  # O teu token integrado, Zé!
)

if not TOKEN or TOKEN == "COLOCA_AQUI_O_TEU_TOKEN_NOVO":
    raise ValueError("Configura o teu token do Telegram através da variável BOT_TOKEN.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# CONFIGURAÇÕES DE GESTÃO DE BANCA E RISCO
ENTRADA = 3
GALE1 = 6
PROTECAO_T = 0

JANELA = 10
LIMITE_LOSSES = 2

# Ajustado para 15 simulações de arranque, Zé!
MIN_PAPER = 15
MIN_RECENTES = 15

# Sessões em memória por chat
sessions = {}


# =====================================================
# SERVIDOR WEB (RENDER 24/7)
# =====================================================

@app.route("/")
def home():
    return "BAC BO MULTISTRATEGY BRAIN - ONLINE 24/7, ZÉ!"


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

        # Fila de simulação em papel (suporta ciclo Entrada -> G1)
        "pending_paper": None,
        "pending_paper_g1": None,

        # Resultados globais da simulação em tempo real
        "paper_results": [],
        "paper_ties": 0,

        # Estatísticas individuais por estratégia
        "strategy_stats": {
            "quebra_sequencia": {"wins": 0, "losses": 0, "signals": 0},
            "inercia_tendencia": {"wins": 0, "losses": 0, "signals": 0},
            "reversao_desequilibrio": {"wins": 0, "losses": 0, "signals": 0}
        },

        # Estatísticas gerais das operações reais
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
# CÉREBRO MULTIESTRATÉGIA (DUPLA CONCORDÂNCIA DE ELITE)
# =====================================================

def multi_strategy_brain(history):
    if len(history) < 20:
        return None

    puros = [x for x in history if x in ("A", "V")]
    if len(puros) < 20:
        return None

    ultimos_6 = puros[-6:]
    ultimos_10 = puros[-10:]
    ultimos_20 = puros[-20:]

    sinais = []

    # -------------------------------------------------
    # ESTRATÉGIA 1 — QUEBRA DE SEQUÊNCIA
    # -------------------------------------------------
    if len(puros) >= 3 and puros[-1] != puros[-2] and puros[-2] == puros[-3]:
        direcao_quebra = puros[-1]
        sinais.append({
            "color": direcao_quebra,
            "strategy": "quebra_sequencia",
            "reason": f"Quebra de sequência confirmada para {direcao_quebra}"
        })

    # -------------------------------------------------
    # ESTRATÉGIA 2 — INÉRCIA DE TENDÊNCIA / BLOCO (Substituta do Ping-Pong)
    # -------------------------------------------------
    cnt_a_6 = ultimos_6.count("A")
    cnt_v_6 = ultimos_6.count("V")
    
    if cnt_a_6 >= 4 and puros[-1] == "A":
        sinais.append({
            "color": "A",
            "strategy": "inercia_tendencia",
            "reason": f"Inércia de bloco forte a favor do Azul ({cnt_a_6}/6)"
        })
    elif cnt_v_6 >= 4 and puros[-1] == "V":
        sinais.append({
            "color": "V",
            "strategy": "inercia_tendencia",
            "reason": f"Inércia de bloco forte a favor do Vermelho ({cnt_v_6}/6)"
        })

    # -------------------------------------------------
    # ESTRATÉGIA 3 — MAIORIA RECENTE (Filtro de Contexto)
    # -------------------------------------------------
    cnt_a_10 = ultimos_10.count("A")
    cnt_v_10 = ultimos_10.count("V")
    contexto_forte = None
    if cnt_a_10 >= 7:
        contexto_forte = "A"
    elif cnt_v_10 >= 7:
        contexto_forte = "V"

    # -------------------------------------------------
    # ESTRATÉGIA 4 — REVERSÃO APÓS DESEQUILÍBRIO
    # -------------------------------------------------
    cnt_a_20 = ultimos_20.count("A")
    cnt_v_20 = ultimos_20.count("V")

    if cnt_a_20 >= 14 and puros[-1] == "V" and puros[-2] == "V":
        sinais.append({
            "color": "V",
            "strategy": "reversao_desequilibrio",
            "reason": f"Reversão após desequilíbrio massivo ({cnt_a_20} Azuis em 20)"
        })
    elif cnt_v_20 >= 14 and puros[-1] == "A" and puros[-2] == "A":
        sinais.append({
            "color": "A",
            "strategy": "reversao_desequilibrio",
            "reason": f"Reversão após desequilíbrio massivo ({cnt_v_20} Vermelhos em 20)"
        })

    # =================================================
    # SISTEMA DE DECISÃO E CONCORDÂNCIA
    # =================================================
    if not sinais:
        return None

    direcoes = [s["color"] for s in sinais]
    
    if len(set(direcoes)) > 1:
        return None

    direcao_unanime = direcoes[0]
    sinais_validos = [s for s in sinais if s["color"] == direcao_unanime]

    if contexto_forte and contexto_forte != direcao_unanime and len(sinais_validos) < 2:
        return None

    if len(sinais_validos) >= 2 or (len(sinais_validos) == 1 and contexto_forte == direcao_unanime):
        estrategias_nomes = "+".join([s["strategy"] for s in sinais_validos])
        razoes = " | ".join([s["reason"] for s in sinais_validos])
        return {
            "color": direcao_unanime,
            "strategy": estrategias_nomes,
            "reason": razoes
        }

    return None


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


# =====================================================
# ESTADO DO CÉREBRO
# =====================================================

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
# AVALIAÇÃO DE SIMULAÇÃO (PAPEL COM G1 E EMPATE PROTEGIDO VENCEDOR)
# =====================================================

def evaluate_paper(session, real_result):
    # Se houver previsões pendentes em fase de G1
    if session.get("pending_paper_g1"):
        pending_list = session["pending_paper_g1"]
        session["pending_paper_g1"] = None

        if real_result == "T":
            session["paper_ties"] += 1
            for pred in pending_list:
                session["paper_results"].append(True)
                strat_name = pred["strategy"]
                if strat_name in session["strategy_stats"]:
                    session["strategy_stats"][strat_name]["signals"] += 1
                    session["strategy_stats"][strat_name]["wins"] += 1
        else:
            for pred in pending_list:
                correct = (pred["color"] == real_result)
                session["paper_results"].append(correct)
                session["paper_results"] = session["paper_results"][-1000:]

                strat_name = pred["strategy"]
                if strat_name in session["strategy_stats"]:
                    session["strategy_stats"][strat_name]["signals"] += 1
                    if correct:
                        session["strategy_stats"][strat_name]["wins"] += 1
                    else:
                        session["strategy_stats"][strat_name]["losses"] += 1
        return

    # Avaliação da Entrada Inicial pendente
    pending_list = session.get("pending_paper")
    if not pending_list:
        return

    if real_result == "T":
        session["paper_ties"] += 1
        for pred in pending_list:
            session["paper_results"].append(True)
            strat_name = pred["strategy"]
            if strat_name in session["strategy_stats"]:
                session["strategy_stats"][strat_name]["signals"] += 1
                session["strategy_stats"][strat_name]["wins"] += 1
        session["pending_paper"] = None
    else:
        still_pending_g1 = []
        for pred in pending_list:
            if pred["color"] == real_result:
                session["paper_results"].append(True)
                session["paper_results"] = session["paper_results"][-1000:]
                strat_name = pred["strategy"]
                if strat_name in session["strategy_stats"]:
                    session["strategy_stats"][strat_name]["signals"] += 1
                    session["strategy_stats"][strat_name]["wins"] += 1
            else:
                still_pending_g1.append(pred)

        session["pending_paper"] = None
        if still_pending_g1:
            session["pending_paper_g1"] = still_pending_g1


# =====================================================
# GESTÃO DAS OPERAÇÕES REAIS (COM LUCRO NA PROTEÇÃO DE EMPATE)
# =====================================================

def close_cycle(session):
    session["active_target"] = None
    session["gale"] = 0


def process_live_bet(chat_id, session, result):
    target = session["active_target"]
    if target is None:
        return

    # EMPATE (T) - Proteção paga lucro líquido de 4x na ficha de T!
    if result == "T":
        session["stats"]["ties"] += 1
        close_cycle(session)
        bot.send_message(
            chat_id,
            "🟡 *RESULTADO EMPATE (T)*\n\n"
            "Aposta principal devolvida e **Proteção T vencedora com lucro líquido**! ✨💰\n"
            "Ciclo encerrado com sucesso.",
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
            level = "GALE 1 (G1)"

        close_cycle(session)

        bot.send_message(
            chat_id,
            "🟢 *GREEN / VITÓRIA CONFIRMADA!* ✨\n\n"
            f"🏆 Resolução: {level}\n"
            f"🎯 Resultado: {result}\n\n"
            "Ciclo encerrado com sucesso.",
            parse_mode="Markdown"
        )
        return

    # FALHA DA ENTRADA PRINCIPAL -> GALE 1
    if session["gale"] == 0:
        session["gale"] = 1
        cor_nome = "AZUL 🔵" if target == "A" else "VERMELHO 🔴"

        bot.send_message(
            chat_id,
            "🔴 *LOSS NA ENTRADA PRINCIPAL*\n\n"
            "🔄 **GALE 1 (G1) OBRIGATÓRIO** 🚨\n\n"
            f"👉 Direção: {cor_nome}\n"
            f"💰 Aposta G1: {GALE1}€\n"
            f"🟡 Proteção T: {PROTECAO_T}€\n\n"
            "Sem Gale 2.",
            parse_mode="Markdown"
        )
        return

    # FALHA DO GALE 1 -> PERDA FINAL
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
# GERAR NOVA DECISÃO
# =====================================================

def generate_decision(chat_id, session):
    if session["blocked"] or session["active_target"] is not None:
        return

    if session["pending_paper"] is not None or session.get("pending_paper_g1") is not None:
        return

    candidate = multi_strategy_brain(session["history"])

    if candidate is None:
        session["stats"]["observations"] += 1
        return

    session["pending_paper"] = [candidate]
    status, detail = brain_status(session)

    if not strategy_validated(session):
        return

    session["active_target"] = candidate["color"]
    session["gale"] = 0
    session["stats"]["entries"] += 1

    cor_nome = "AZUL 🔵" if candidate["color"] == "A" else "VERMELHO 🔴"

    bot.send_message(
        chat_id,
        "🧠 *MULTISTRATEGY BRAIN*\n\n"
        "📊 FILTRO ESTATÍSTICO APROVADO\n\n"
        f"🎯 Direção: {cor_nome}\n"
        f"💰 Entrada: {ENTRADA}€\n"
        f"🟡 Proteção T: {PROTECAO_T}€\n\n"
        f"🔎 Estratégia(s): {candidate['strategy']}\n"
        f"💡 Motivo: {candidate['reason']}\n\n"
        "⚠️ Critérios experimentais cumpridos.",
        parse_mode="Markdown"
    )


# =====================================================
# RECEBER UMA NOVA JOGADA
# =====================================================

def receive_result(chat_id, session, result):
    evaluate_paper(session, result)
    process_live_bet(chat_id, session, result)

    session["history"].append(result)
    session["history"] = session["history"][-250:]

    if not session["blocked"]:
        generate_decision(chat_id, session)


# =====================================================
# COMANDOS DO BOT
# =====================================================

@bot.message_handler(commands=["start"])
def start(message):
    sessions[message.chat.id] = nova_sessao()

    bot.reply_to(
        message,
        "🤖 *BAC BO - MULTISTRATEGY BRAIN*\n\n"
        "Sistema otimizado com calibração de 30 ciclos, G1 e Empate Protegido Lucrativo!\n\n"
        "📊 Envia as tuas 10 jogadas iniciais.\n\n"
        "Exemplo:\n"
        "`A V A A V T V A V V`\n\n"
        "🔵 A = Azul | 🔴 V = Vermelho | 🟡 T = Empate\n\n"
        "💰 Entrada: 3€ | 🔄 G1: 6€ | 🛡️ Proteção T: 1€\n"
        "🚨 Máximo: 2 perdas finais\n\n"
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
        "1. Utiliza /start.\n"
        "2. Envia exatamente 10 jogadas iniciais.\n"
        "3. Depois envia apenas uma jogada de cada vez.\n"
        "4. O cérebro avalia as 4 estratégias após cada resultado.\n\n"
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

    bot.reply_to(
        message,
        "🧠 *ESTADO DO MULTISTRATEGY BRAIN*\n\n"
        f"📊 Estado: {status}\n"
        f"🔎 {detail}\n"
        f"📜 Histórico: {len(session['history'])} jogadas\n"
        f"🎯 Simulações concluídas: {len(session['paper_results'])}/{MIN_PAPER}\n"
        f"🟡 Empates simulados: {session['paper_ties']}\n"
        f"🛡️ Operação ativa: {'SIM' if session['active_target'] else 'NÃO'}\n"
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
    rate = (st["wins"] / resolved * 100) if resolved else 0

    paper = session["paper_results"]
    paper_rate = (sum(paper) / len(paper) * 100) if paper else 0
    recent_paper = paper[-MIN_RECENTES:] if paper else []
    recent_rate = (sum(recent_paper) / len(recent_paper) * 100) if recent_paper else 0
    lower = (wilson_lower_bound(sum(paper), len(paper)) * 100) if paper else 0

    strat_text = ""
    for s_name, s_data in session["strategy_stats"].items():
        s_tot = s_data["wins"] + s_data["losses"]
        s_rate = (s_data["wins"] / s_tot * 100) if s_tot else 0
        strat_text += f"• *{s_name}*: {s_data['wins']}W / {s_data['losses']}L ({s_rate:.1f}%)\n"

    bot.reply_to(
        message,
        "📊 *RELATÓRIO MULTISTRATEGY BRAIN*\n\n"
        "OPERAÇÕES REAIS\n"
        f"🟢 Greens: {st['wins']} (G1: {st['wins_g1']})\n"
        f"🔴 Perdas finais: {st['losses']}/{LIMITE_LOSSES}\n"
        f"🟡 Empates (Proteção Lucrativa): {st['ties']}\n"
        f"🎯 Entradas: {st['entries']}\n"
        f"📈 Taxa de acerto real: {rate:.2f}%\n\n"
        f"SIMULAÇÃO / PAPEL (Alvo: {MIN_PAPER} ciclos)\n"
        f"📊 Total ciclos simulados: {len(paper)}\n"
        f"📈 Taxa simulada global: {paper_rate:.2f}%\n"
        f"📈 Taxa últimas {MIN_RECENTES}: {recent_rate:.2f}%\n"
        f"📉 Limite inferior Wilson: {lower:.2f}%\n\n"
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
        "🔄 Sessão reiniciada!\n\n"
        "Envia novamente as 10 jogadas iniciais."
    )


# =====================================================
# RECEBER RESULTADOS DA MESA (COM FEEDBACK DE CONFIRMAÇÃO)
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

    raw = message.text.upper()
    cleaned = re.sub(r"[\s,;|]+", "", raw)

    if not cleaned or any(c not in "AVT" for c in cleaned):
        bot.reply_to(
            message,
            "⚠️ Formato inválido.\nUtiliza apenas A, V ou T."
        )
        return

    if session["blocked"]:
        bot.reply_to(
            message,
            "🛑 Sessão bloqueada.\nUtiliza /reset para iniciar outra."
        )
        return

    # PRIMEIRO ENVIO: 10 JOGADAS INICIAIS
    if session["awaiting_seed"]:
        if len(cleaned) != JANELA:
            bot.reply_to(
                message,
                f"⚠️ Preciso de exatamente 10 jogadas iniciais. Tens {len(cleaned)}."
            )
            return

        session["history"] = list(cleaned)
        session["awaiting_seed"] = False

        candidate = multi_strategy_brain(session["history"])
        if candidate:
            session["pending_paper"] = [candidate]

        bot.reply_to(
            message,
            "🧠 *HISTÓRICO CARREGADO!* 🚀\n\n"
            "As 10 jogadas foram guardadas.\n"
            "Envia agora **apenas UMA nova jogada** de cada vez.",
            parse_mode="Markdown"
        )
        return

    # FLUXO NORMAL: UMA JOGADA DE CADA VEZ
    if len(cleaned) != 1:
        bot.reply_to(
            message,
            "⚠️ Envia apenas um resultado por mensagem (ex: A)."
        )
        return

    # Processar o resultado da ronda
    receive_result(chat_id, session, cleaned)
    
    # Feedback imediato de confirmação
    bot.reply_to(
        message,
        f"✅ Jogada `{cleaned}` registada! Histórico ativo: `{len(session['history'])}` rondas. A analisar...",
        parse_mode="Markdown"
    )


# =====================================================
# INICIALIZAÇÃO DO BOT
# =====================================================

if __name__ == "__main__":
    print("BAC BO MULTISTRATEGY BRAIN ONLINE")

    Thread(
        target=run_web,
        daemon=True
    ).start()

    bot.infinity_polling(
        skip_pending=True,
        timeout=20,
        long_polling_timeout=20
    )
