import os
import re
from math import sqrt
from threading import Thread

import telebot
from flask import Flask

# =====================================================
# BAC BO BRAIN - ADAPTIVE TABLE & GALE 2 REGIME ENGINE
# Motor de Bac Bo (P / B / E) com Estratégia Única, Concordância de Fatores e Adaptação no Gale 2
# =====================================================

TOKEN = os.getenv(
    "BOT_TOKEN",
    "8922303337:AAEfiGQK15Cd4B4SsW-FS97Fq6QyPH2aUEs"
)

if not TOKEN or TOKEN == "COLOCA_AQUI_O_TEU_TOKEN_NOVO":
    raise ValueError("Configura o teu token do Telegram através da variável BOT_TOKEN.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# CONFIGURAÇÕES DE GESTÃO DE BANCA, RISCO E ADAPTAÇÃO (BAC BO: P / B / E)
ENTRADA_BASE = 4        # Aposta base (Entrada)
GALE1_VALOR = 8         # Aposta no Gale 1 (G1)
GALE2_VALOR = 16        # Aposta no Gale 2 (G2)

JANELA = 10             # Jogadas iniciais para arrancar
LIMITE_LOSSES = 2       # Máximo de ciclos perdidos (Entrada + G1 + G2 falhados)
ESPERA_POS_GREEN = 2    # Espera mínima de rondas após GREEN
PAUSA_POS_GALE2 = 3     # Rondinhas extra de leitura/pausa quando o ciclo chega ao Gale 2
MIN_CONCORDANCIA_BASE = 3  # Mínimo de fatores em concordância para entrar

MIN_PAPER = 0           # Sem filtro experimental prévio: entra logo em real
MIN_RECENTES = 10       # Janela recente para consulta de estatísticas

# Sessões em memória por chat
sessions = {}


# =====================================================
# SERVIDOR WEB (RENDER 24/7)
# =====================================================

@app.route("/")
def home():
    return "BAC BO BRAIN - ONLINE 24/7, ZÉ!"


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
        "history": [],          # Lista de resultados ("P", "B", "E")
        "awaiting_seed": True,

        "active_side": None,    # Lado ativo: "P" (Jogador) ou "B" (Banca)
        "active_reason": "",
        "active_strategy": "",
        "gale": 0,              # 0 = Entrada, 1 = Gale 1, 2 = Gale 2
        "reached_gale2": False, # Marca se o ciclo atual atingiu Gale 2
        "blocked": False,
        "green_wait_rounds": 0, # Rondinhas restantes de espera obrigatória após GREEN
        "g2_wait_rounds": 0,    # Rondinhas de adaptação após chegar ao Gale 2

        # Estado adaptativo da mesa e aprendizagem pós-Gale 2 / pós-loss
        "table_regime": "MISTA", # "SEQUENCIAS_LIMPAS", "PICADA_ERRATICA", "MISTA"
        "required_concordance": MIN_CONCORDANCIA_BASE,
        "favored_side": None,
        "side_penalty": {"P": 0, "B": 0},
        "error_memory": [],
        "g2_adapt_log": [],
        "strategy_penalty": {
            "concordancia_mesa_bacbo": 0
        },
        "cooldown_by_side": {
            "P": 0,
            "B": 0
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
            "concordancia_mesa_bacbo": {"wins": 0, "losses": 0, "signals": 0}
        },

        # Estatísticas gerais das operações reais
        "stats": {
            "wins": 0,
            "wins_g1": 0,
            "wins_g2": 0,
            "losses": 0,
            "t_hits": 0,
            "entries": 0,
            "observations": 0,
            "gale2_events": 0
        }
    }


# =====================================================
# CONVERSÃO DE RESULTADO PARA BAC BO (P / B / E)
# =====================================================

def parse_token_to_outcome(token):
    t = token.strip().upper()
    if t in ("P", "PLAYER", "J", "JOGADOR"):
        return "P"
    if t in ("B", "BANK", "BANKER", "BANCA"):
        return "B"
    if t in ("E", "T", "TIE", "EMPATE", "X"):
        return "E"
    return None


def format_lado_nome(side):
    nomes = {
        "P": "Jogador (P)",
        "B": "Banca (B)",
        "E": "Empate (E)"
    }
    return nomes.get(side, side)


# =====================================================
# LEITURA E ADAPTAÇÃO AO REGIME DA MESA (ESPECIALMENTE NO GALE 2)
# =====================================================

def calcular_streak_atual(pb_hist):
    if not pb_hist:
        return None, 0
    ultimo = pb_hist[-1]
    cont = 0
    for item in reversed(pb_hist):
        if item == ultimo:
            cont += 1
        else:
            break
    return ultimo, cont


def classificar_mesa(history):
    """Analisa o histórico para identificar se a mesa está em sequências limpas, picada/errática ou mista."""
    pb_hist = [x for x in history if x in ("P", "B")]
    ult_12 = history[-12:] if history else []
    empates_12 = ult_12.count("E")

    if len(pb_hist) < 6:
        return "MISTA", 0.5, empates_12

    ult_8 = pb_hist[-8:]
    mudancas = sum(1 for i in range(1, len(ult_8)) if ult_8[i] != ult_8[i - 1])
    taxa_alternancia = mudancas / (len(ult_8) - 1)

    _, streak_atual = calcular_streak_atual(pb_hist)

    # Conta blocos de repetição (>= 2 iguais seguidos) nas últimas 8 decisões P/B
    repeticoes_recentes = sum(1 for i in range(1, len(ult_8)) if ult_8[i] == ult_8[i - 1])

    if taxa_alternancia <= 0.42 and (repeticoes_recentes >= 3 or streak_atual >= 3):
        regime = "SEQUENCIAS_LIMPAS"
    elif taxa_alternancia >= 0.72 and streak_atual <= 1:
        regime = "PICADA_ERRATICA"
    else:
        regime = "MISTA"

    return regime, round(taxa_alternancia, 2), empates_12


def tick_learning_cooldowns(session):
    for side in ("P", "B"):
        if session["cooldown_by_side"][side] > 0:
            session["cooldown_by_side"][side] -= 1
    if session.get("green_wait_rounds", 0) > 0:
        session["green_wait_rounds"] -= 1
    if session.get("g2_wait_rounds", 0) > 0:
        session["g2_wait_rounds"] -= 1


def adaptar_ao_gale2(session, lado_apostado, resultado_final, foi_win):
    """
    Executado sempre que um ciclo chega ao Gale 2:
    lê como a mesa está naquele momento e adapta o comportamento do robô.
    """
    regime, alt, empates_12 = classificar_mesa(session["history"])
    pb_hist = [x for x in session["history"] if x in ("P", "B")]
    ultimo_pb, streak = calcular_streak_atual(pb_hist)

    session["stats"]["gale2_events"] += 1
    session["table_regime"] = regime
    session["g2_wait_rounds"] = max(session.get("g2_wait_rounds", 0), PAUSA_POS_GALE2)

    if regime == "SEQUENCIAS_LIMPAS":
        # Em sequências limpas que exigiram Gale 2, o robô ajusta-se a favor do fluxo limpo se houver streak
        session["required_concordance"] = MIN_CONCORDANCIA_BASE
        if ultimo_pb in ("P", "B") and streak >= 2:
            session["favored_side"] = ultimo_pb
        else:
            session["favored_side"] = None
        leitura_mesa = f"Mesa em SEQUÊNCIAS LIMPAS (alternância {alt:.0%}, streak {streak} em {ultimo_pb or '-'})"
    elif regime == "PICADA_ERRATICA":
        # Em mesa picada/errática que exigiu Gale 2, sobe exigência de concordância e evita insistir cego
        session["required_concordance"] = min(5, MIN_CONCORDANCIA_BASE + 1)
        session["favored_side"] = None
        if lado_apostado in ("P", "B"):
            session["side_penalty"][lado_apostado] = min(3, session["side_penalty"][lado_apostado] + 1)
            session["cooldown_by_side"][lado_apostado] = max(session["cooldown_by_side"][lado_apostado], 3)
        leitura_mesa = f"Mesa PICADA/ERRÁTICA (alternância {alt:.0%}) -> exige mais concordância ({session['required_concordance']})"
    else:
        session["required_concordance"] = MIN_CONCORDANCIA_BASE
        session["favored_side"] = None
        if not foi_win and lado_apostado in ("P", "B"):
            session["side_penalty"][lado_apostado] = min(3, session["side_penalty"][lado_apostado] + 1)
        leitura_mesa = f"Mesa MISTA (alternância {alt:.0%}, empates recentes {empates_12}/12)"

    if empates_12 >= 3:
        leitura_mesa += f" | Atenção a empates ({empates_12}/12)"

    estado_g2 = "GREEN no G2" if foi_win else f"LOSS no G2 ({resultado_final})"
    diagnostico = f"[{estado_g2}] {leitura_mesa}"

    session["g2_adapt_log"].append({
        "side": lado_apostado,
        "outcome": resultado_final,
        "won": foi_win,
        "regime": regime,
        "diagnosis": diagnostico
    })
    session["g2_adapt_log"] = session["g2_adapt_log"][-40:]
    return diagnostico


def registrar_autopsia_loss(session, lado_apostado, estrategia, ult_resultado, contexto_hist):
    lado_txt = format_lado_nome(lado_apostado)
    if ult_resultado in ("P", "B") and ult_resultado != lado_apostado:
        motivo_erro = f"A mesa puxou {format_lado_nome(ult_resultado)} contra {lado_txt}"
    else:
        motivo_erro = f"Falha em {lado_txt} com resultado {ult_resultado}"

    if estrategia in session["strategy_penalty"]:
        session["strategy_penalty"][estrategia] = min(session["strategy_penalty"][estrategia] + 1, 3)

    if lado_apostado in session["side_penalty"]:
        session["side_penalty"][lado_apostado] = min(session["side_penalty"][lado_apostado] + 1, 3)

    if lado_apostado in session["cooldown_by_side"]:
        session["cooldown_by_side"][lado_apostado] = max(session["cooldown_by_side"][lado_apostado], 3)

    session["error_memory"].append({
        "side": lado_apostado,
        "strategy": estrategia,
        "last_outcome": ult_resultado,
        "context": contexto_hist[-6:],
        "diagnosis": motivo_erro
    })
    session["error_memory"] = session["error_memory"][-50:]
    return motivo_erro


def registar_acerto_aprendizagem(session, lado_apostado, estrategia):
    if estrategia in session["strategy_penalty"] and session["strategy_penalty"][estrategia] > 0:
        session["strategy_penalty"][estrategia] -= 1
    if lado_apostado in session["side_penalty"] and session["side_penalty"][lado_apostado] > 0:
        session["side_penalty"][lado_apostado] = max(0, session["side_penalty"][lado_apostado] - 1)
    if lado_apostado in session["cooldown_by_side"] and session["cooldown_by_side"][lado_apostado] > 0:
        session["cooldown_by_side"][lado_apostado] -= 1


# =====================================================
# CÉREBRO DE BAC BO (1 ESTRATÉGIA + CONCORDÂNCIA DE FATORES)
# =====================================================

def bacbo_brain(session):
    # Respeita espera mínima após GREEN e pausa de adaptação após Gale 2
    if session.get("green_wait_rounds", 0) > 0 or session.get("g2_wait_rounds", 0) > 0:
        return None

    history = session["history"]
    pb_hist = [x for x in history if x in ("P", "B")]
    if len(pb_hist) < 8:
        return None

    regime, taxa_alt, empates_12 = classificar_mesa(history)
    session["table_regime"] = regime

    # Evita entrar se houver enxurrada de empates nas últimas 12 rondas
    if empates_12 >= 4:
        return None

    ultimo_pb, streak = calcular_streak_atual(pb_hist)
    ult_10_pb = pb_hist[-10:]
    cont_p_10 = ult_10_pb.count("P")
    cont_b_10 = ult_10_pb.count("B")
    ultimo_erro = session["error_memory"][-1] if session["error_memory"] else None

    min_conc = session.get("required_concordance", MIN_CONCORDANCIA_BASE)
    melhor_candidato = None

    for lado in ("P", "B"):
        oposto = "B" if lado == "P" else "P"
        cont_lado_10 = cont_p_10 if lado == "P" else cont_b_10
        cont_op_10 = cont_b_10 if lado == "P" else cont_p_10

        fatores = []

        # Fator 1: Alinhamento com o regime atual da mesa
        if regime == "SEQUENCIAS_LIMPAS" and ultimo_pb == lado and streak >= 2:
            fatores.append(f"Sequência limpa em {lado} ({streak} seguidos)")
        elif regime == "PICADA_ERRATICA" and ultimo_pb == oposto and taxa_alt >= 0.72:
            fatores.append(f"Ritmo picado favorece alternância para {lado}")
        elif regime == "MISTA" and ultimo_pb == lado and streak >= 2:
            fatores.append(f"Tração recente em {lado} ({streak} seguidos)")

        # Fator 2: Equilíbrio / pressão de frequência nas últimas 10 mãos P/B (entre 3 e 7)
        if 3 <= cont_lado_10 <= 7:
            fatores.append(f"Frequência equilibrada ({cont_lado_10}/10)")

        # Fator 3: Sem cooldown ativo neste lado
        if session["cooldown_by_side"].get(lado, 0) == 0:
            fatores.append("Sem cooldown")

        # Fator 4: Baixa penalidade de erro/risco neste lado
        if session["side_penalty"].get(lado, 0) <= 1:
            fatores.append("Risco controlado no lado")

        # Fator 5: Não repete o lado do último loss final nem conflita com lado vetado após G2
        if not (ultimo_erro and ultimo_erro.get("side") == lado):
            if session.get("favored_side") in (None, lado):
                fatores.append("Sem bloqueio por perda/G2 recente")

        if len(fatores) >= min_conc:
            pen = session["strategy_penalty"].get("concordancia_mesa_bacbo", 0) + session["side_penalty"].get(lado, 0)
            score = len(fatores) - (0.30 * pen)
            motivo = (
                f"[{regime} | {len(fatores)}/5 fatores] "
                + " | ".join(fatores)
                + f" (P:{cont_p_10}/10, B:{cont_b_10}/10, E:{empates_12}/12)"
            )

            if melhor_candidato is None or score > melhor_candidato["score"]:
                melhor_candidato = {
                    "side": lado,
                    "strategy": "concordancia_mesa_bacbo",
                    "reason": motivo,
                    "score": score
                }

    if melhor_candidato is None:
        return None

    return {
        "side": melhor_candidato["side"],
        "strategy": melhor_candidato["strategy"],
        "reason": melhor_candidato["reason"]
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
    regime = session.get("table_regime", "MISTA")
    req_c = session.get("required_concordance", MIN_CONCORDANCIA_BASE)
    espera_g = session.get("green_wait_rounds", 0)
    espera_g2 = session.get("g2_wait_rounds", 0)

    avisos = []
    if espera_g > 0:
        avisos.append(f"Espera pós-GREEN: {espera_g}")
    if espera_g2 > 0:
        avisos.append(f"Adaptação pós-G2: {espera_g2}")
    if not avisos:
        avisos.append("A aguardar concordância válida")

    return (
        f"MODO REAL BAC BO ({regime})",
        f"Concordância mín. {req_c}/5 | {total} ciclos | {' | '.join(avisos)}"
    )


# =====================================================
# AVALIAÇÃO DE CICLO (BAC BO: P / B / E, ATÉ G2)
# =====================================================

def evaluate_paper(session, outcome):
    if outcome == "E":
        session["paper_t"] += 1

    # Fase Gale 2
    if session.get("pending_paper_g2"):
        pred = session["pending_paper_g2"]
        session["pending_paper_g2"] = None

        acertou = (outcome == pred["side"])
        session["paper_results"].append(acertou)
        session["paper_results"] = session["paper_results"][-1000:]

        strat = pred["strategy"]
        if strat in session["strategy_stats"]:
            session["strategy_stats"][strat]["signals"] += 1
            if acertou:
                session["strategy_stats"][strat]["wins"] += 1
                registar_acerto_aprendizagem(session, pred["side"], strat)
                adaptar_ao_gale2(session, pred["side"], outcome, foi_win=True)
            else:
                session["strategy_stats"][strat]["losses"] += 1
                registrar_autopsia_loss(session, pred["side"], strat, outcome, session["history"])
                adaptar_ao_gale2(session, pred["side"], outcome, foi_win=False)
        return

    # Fase Gale 1
    if session.get("pending_paper_g1"):
        pred = session["pending_paper_g1"]
        session["pending_paper_g1"] = None

        if outcome == pred["side"]:
            session["paper_results"].append(True)
            session["paper_results"] = session["paper_results"][-1000:]
            strat = pred["strategy"]
            if strat in session["strategy_stats"]:
                session["strategy_stats"][strat]["signals"] += 1
                session["strategy_stats"][strat]["wins"] += 1
            registar_acerto_aprendizagem(session, pred["side"], strat)
        else:
            # Falhou no Gale 1 -> passa para Gale 2
            session["pending_paper_g2"] = pred
        return

    # Fase Entrada inicial
    pred = session.get("pending_paper")
    if not pred:
        return

    session["pending_paper"] = None

    if outcome == pred["side"]:
        session["paper_results"].append(True)
        session["paper_results"] = session["paper_results"][-1000:]
        strat = pred["strategy"]
        if strat in session["strategy_stats"]:
            session["strategy_stats"][strat]["signals"] += 1
            session["strategy_stats"][strat]["wins"] += 1
        registar_acerto_aprendizagem(session, pred["side"], strat)
    else:
        # Falhou na Entrada -> passa para Gale 1
        session["pending_paper_g1"] = pred


# =====================================================
# GESTÃO DAS OPERAÇÕES REAIS (BAC BO: P / B / E, ATÉ G2)
# =====================================================

def close_cycle(session, foi_green=False, veio_de_g2=False):
    session["active_side"] = None
    session["active_reason"] = ""
    session["active_strategy"] = ""
    session["gale"] = 0
    session["reached_gale2"] = False
    if foi_green:
        session["green_wait_rounds"] = max(session.get("green_wait_rounds", 0), ESPERA_POS_GREEN)
    if veio_de_g2:
        session["g2_wait_rounds"] = max(session.get("g2_wait_rounds", 0), PAUSA_POS_GALE2)


def process_live_bet(chat_id, session, outcome, raw_label):
    lado = session["active_side"]
    if lado is None:
        return

    if outcome == "E":
        session["stats"]["t_hits"] += 1

    # ACERTO NO LADO ESCOLHIDO (P OU B)
    if outcome == lado:
        strat = session["active_strategy"]
        veio_g2 = (session["gale"] == 2)
        nota_g2 = ""

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
            nota_g2 = "\n🧠 " + adaptar_ao_gale2(session, lado, outcome, foi_win=True)

        registar_acerto_aprendizagem(session, lado, strat)
        close_cycle(session, foi_green=True, veio_de_g2=veio_g2)

        bot.send_message(
            chat_id,
            "🟢 *GREEN / VITÓRIA CONFIRMADA!* ✨\n\n"
            f"🏆 Resolução: {nivel}\n"
            f"🎯 Resultado: {raw_label} ({outcome})\n"
            f"🎲 Lado: {format_lado_nome(lado)}{nota_g2}\n\n"
            f"Ciclo encerrado com sucesso. A aguardar pelo menos {ESPERA_POS_GREEN} rondas antes de nova entrada.",
            parse_mode="Markdown"
        )
        return

    # FALHA NA ENTRADA -> VAI PARA GALE 1 (G1)
    if session["gale"] == 0:
        session["gale"] = 1

        bot.send_message(
            chat_id,
            "🔴 *LOSS NA ENTRADA PRINCIPAL*\n\n"
            "🔄 **GALE 1 (G1)** 🚨\n\n"
            f"🎲 Lado: *{format_lado_nome(lado)}*\n"
            f"💰 Aposta: {GALE1_VALOR}€ | Próximo passo: Gale 2.",
            parse_mode="Markdown"
        )
        return

    # FALHA NO GALE 1 -> VAI PARA GALE 2 (G2)
    if session["gale"] == 1:
        session["gale"] = 2
        session["reached_gale2"] = True

        bot.send_message(
            chat_id,
            "🔴 *LOSS NO GALE 1 (G1)*\n\n"
            "🔄 **GALE 2 (G2)** 🚨\n\n"
            f"🎲 Lado: *{format_lado_nome(lado)}*\n"
            f"💰 Aposta: {GALE2_VALOR}€ | Último Gale do ciclo.",
            parse_mode="Markdown"
        )
        return

    # FALHA NO GALE 2 -> LEITURA DA MESA, AUTÓPSIA E PERDA FINAL DO CICLO
    strat = session["active_strategy"]
    diagnostico = registrar_autopsia_loss(session, lado, strat, outcome, session["history"])
    adapt_g2 = adaptar_ao_gale2(session, lado, outcome, foi_win=False)
    session["stats"]["losses"] += 1
    close_cycle(session, foi_green=False, veio_de_g2=True)
    losses = session["stats"]["losses"]

    if losses >= LIMITE_LOSSES:
        session["blocked"] = True
        bot.send_message(
            chat_id,
            "🚨 *LIMITE DE PERDAS ATINGIDO!* 🛑\n\n"
            f"🔴 Perdas finais: {losses}/{LIMITE_LOSSES}\n"
            f"🧩 Autópsia: {diagnostico}\n"
            f"🧠 Adaptação G2: {adapt_g2}\n\n"
            "🛑 Sessão bloqueada de imediato.\n"
            "Utiliza /reset para iniciar uma nova sessão.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id,
            "❌ *LOSS FINAL - GALE 2 FALHADO*\n\n"
            f"🔴 Perdas finais: {losses}/{LIMITE_LOSSES}\n"
            f"🧩 Autópsia: {diagnostico}\n"
            f"🧠 Adaptação G2: {adapt_g2}\n\n"
            "O robô leu o estado da mesa e ajustou a exigência de concordância para proteger a sessão.",
            parse_mode="Markdown"
        )


# =====================================================
# GERAR NOVA DECISÃO DE BAC BO (P / B)
# =====================================================

def generate_decision(chat_id, session):
    if session["blocked"] or session["active_side"] is not None:
        return

    if (
        session["pending_paper"] is not None
        or session.get("pending_paper_g1") is not None
        or session.get("pending_paper_g2") is not None
    ):
        return

    candidate = bacbo_brain(session)

    if candidate is None:
        session["stats"]["observations"] += 1
        return

    session["pending_paper"] = candidate

    lado = candidate["side"]
    session["active_side"] = lado
    session["active_reason"] = candidate["reason"]
    session["active_strategy"] = candidate["strategy"]
    session["gale"] = 0
    session["reached_gale2"] = False
    session["stats"]["entries"] += 1

    bot.send_message(
        chat_id,
        "🧠 *BAC BO BRAIN*\n\n"
        "⚡ ENTRADA REAL IMEDIATA (CONCORDÂNCIA DE FATORES)\n\n"
        f"🎲 Entrar em: *{format_lado_nome(lado)}*\n"
        f"💰 Entrada: {ENTRADA_BASE}€ | 🔄 Gale 1: {GALE1_VALOR}€ | 🔄 Gale 2: {GALE2_VALOR}€\n"
        "Adaptação automática ao regime da mesa no Gale 2\n\n"
        f"🔎 Estratégia: {candidate['strategy']}\n"
        f"💡 Concordância: {candidate['reason']}",
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

    bot.reply_to(
        message,
        "🤖 *BAC BO BRAIN*\n\n"
        "Sistema de Bac Bo (P / B / E) com estratégia única, concordância entre fatores, espera pós-GREEN e adaptação automática ao regime da mesa no Gale 2!\n\n"
        f"📊 Envia as tuas {JANELA} jogadas iniciais (P, B ou E).\n\n"
        "Exemplo:\n"
        "`P P B E B B P B P P`\n\n"
        f"💰 Entrada: {ENTRADA_BASE}€ | 🔄 G1: {GALE1_VALOR}€ | 🔄 G2: {GALE2_VALOR}€\n"
        f"⏱️ Espera após GREEN: mín. {ESPERA_POS_GREEN} rondas\n"
        f"🚨 Máximo: {LIMITE_LOSSES} perdas finais\n\n"
        "/stats - Estatísticas detalhadas\n"
        "/status - Estado da mesa, concordância e G2\n"
        "/reset - Reiniciar sessão\n"
        "/ajuda - Ajuda",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["ajuda"])
def help_command(message):
    bot.reply_to(
        message,
        "📖 *COMO UTILIZAR (BAC BO)*\n\n"
        f"1. Utiliza /start.\n"
        f"2. Envia exatamente {JANELA} resultados iniciais (P = Jogador, B = Banca, E = Empate).\n"
        "3. Depois envia apenas um resultado de cada vez.\n"
        "4. O robô só entra quando há concordância entre fatores, espera pelo menos 2 rondas após GREEN e adapta-se à mesa quando chega ao Gale 2.",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["status"])
def status_command(message):
    session = sessions.get(message.chat.id)
    if session is None:
        bot.reply_to(message, "Utiliza /start primeiro.")
        return

    status, detail = brain_status(session)
    ativa_txt = format_lado_nome(session["active_side"]) if session["active_side"] else "NÃO"
    ultimo_g2 = session["g2_adapt_log"][-1]["diagnosis"] if session.get("g2_adapt_log") else "Nenhum ciclo chegou ao Gale 2 ainda"

    bot.reply_to(
        message,
        "🧠 *ESTADO DO BAC BO BRAIN*\n\n"
        f"📊 Estado: {status}\n"
        f"🔎 {detail}\n"
        f"📜 Histórico: {len(session['history'])} jogadas\n"
        f"🎯 Ciclos concluídos: {len(session['paper_results'])}\n"
        f"⚡ Operação ativa: {ativa_txt}\n"
        f"🔄 Eventos Gale 2: {session['stats']['gale2_events']}\n"
        f"🔍 Última leitura G2: {ultimo_g2}\n"
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
        "📊 *RELATÓRIO BAC BO BRAIN*\n\n"
        "OPERAÇÕES REAIS\n"
        f"🟢 Greens: {st['wins']} (G1: {st['wins_g1']} | G2: {st['wins_g2']})\n"
        f"🔴 Perdas finais: {st['losses']}/{LIMITE_LOSSES}\n"
        f"🔄 Chegadas ao Gale 2: {st['gale2_events']}\n"
        f"🎯 Entradas: {st['entries']}\n"
        f"📈 Taxa de acerto real: {taxa_real:.2f}%\n\n"
        "HISTÓRICO DE CICLOS\n"
        f"📊 Total ciclos concluídos: {len(paper)}\n"
        f"📈 Taxa global: {taxa_papel:.2f}%\n"
        f"📈 Taxa últimas {MIN_RECENTES}: {taxa_recente:.2f}%\n"
        f"📉 Limite inferior Wilson: {wilson:.2f}%\n\n"
        "DESEMPENHO E ADAPTAÇÃO POR ESTRATÉGIA\n"
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
        f"Envia novamente as {JANELA} jogadas iniciais (P, B ou E)."
    )


# =====================================================
# RECEBER RESULTADOS DA MESA (BAC BO)
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

    tokens = re.findall(r"\b[PBEJTX]\b", message.text.upper())
    if not tokens:
        bot.reply_to(
            message,
            "⚠️ Formato inválido.\nUtiliza P (Jogador), B (Banca) ou E (Empate)."
        )
        return

    parsed = []
    for tk in tokens:
        outcome = parse_token_to_outcome(tk)
        if outcome is None:
            bot.reply_to(
                message,
                f"⚠️ Valor inválido: `{tk}`.\nUsa P (Jogador), B (Banca) ou E (Empate).",
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
            "Envia agora **apenas UMA nova jogada** (`P`, `B` ou `E`) de cada vez para começar a analisar.",
            parse_mode="Markdown"
        )
        return

    # FLUXO NORMAL: UMA JOGADA DE CADA VEZ
    if len(parsed) != 1:
        bot.reply_to(
            message,
            "⚠️ Envia apenas um resultado por mensagem (ex: P, B ou E)."
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
    print("BAC BO BRAIN ONLINE")

    Thread(
        target=run_web,
        daemon=True
    ).start()

    bot.infinity_polling(
        skip_pending=True,
        timeout=20,
        long_polling_timeout=20
    )
