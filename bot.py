import os
import re
from math import sqrt
from threading import Thread

import telebot
from flask import Flask

# =====================================================
# BAC BO SNIPER BRAIN - ZERO GALE + CONCORDÂNCIA MULTI-ESTRATÉGIA
# Entrada: 1 Cor (P/Azul ou B/Vermelho) + T (Empate) | T = WIN | Sem Gale
# =====================================================

TOKEN = os.getenv(
    "BOT_TOKEN",
    "8922303337:AAEfiGQK15Cd4B4SsW-FS97Fq6QyPH2aUEs"
)

if not TOKEN or TOKEN == "COLOCA_AQUI_O_TEU_TOKEN_NOVO":
    raise ValueError("Configura o teu token do Telegram através da variável BOT_TOKEN.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# CONFIGURAÇÕES DE GESTÃO E FILTROS (SEM GALE)
APOSTA_COR = 4.0            # Valor base na Cor (P ou B)
APOSTA_T = 0.5              # Valor base de cobertura no T (Empate)

JANELA = 12                 # Jogadas iniciais para leitura sólida da mesa
LIMITE_LOSSES = 3           # Máximo de losses diretos na sessão (sem gale)
ESPERA_POS_GREEN = 3        # Espera mínima de rondas após cada GREEN (não entra seguido)
ESPERA_POS_LOSS = 3         # Espera obrigatória após cada LOSS para reavaliar a mesa
MIN_CONCORDANCIA = 4        # Exige pelo menos 4 de 6 estratégias/motores em concordância

# TRAVÕES ANTI-SEQUÊNCIA INFINITA (NUNCA SEGUE V V V V V V... NEM CHOP ETERNO)
MAX_STREAK_SEGUIR = 3       # Só acompanha sequência até 3 seguidos; >= 4 bloqueia seguimento
MAX_STREAK_QUEBRA = 4       # Só tenta quebra em 3 ou 4 seguidos; >= 5 bloqueia por perigo de dragon
MAX_CHOP_SEGUIR = 4         # Só acompanha alternância (P-B-P-B) até 4 trocas; >= 5 bloqueia
MAX_CONSEC_WINS_SAME_PATTERN = 2  # Não repete o mesmo padrão mais de 2 wins seguidos

MIN_RECENTES = 10           # Janela recente para consulta de estatísticas

sessions = {}


# =====================================================
# SERVIDOR WEB (RENDER 24/7)
# =====================================================

@app.route("/")
def home():
    return "BAC BO SNIPER BRAIN (ZERO GALE) - ONLINE 24/7!"


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
        "history": [],              # Histórico normalizado: "P", "B", "T"
        "awaiting_seed": True,

        "active_side": None,        # Lado ativo: "P" (Jogador/Azul) ou "B" (Banca/Vermelho) + "T"
        "active_reason": "",
        "active_pattern": "",
        "blocked": False,

        # Pausas e travões de cadência
        "wait_rounds": 0,           # Rondinhas obrigatórias de espera antes de avaliar nova entrada
        "last_pattern_used": "",
        "consecutive_pattern_wins": 0,

        # Aprendizagem e arrefecimento por lado/padrão
        "cooldown_by_side": {"P": 0, "B": 0},
        "side_losses": {"P": 0, "B": 0},
        "error_memory": [],

        # Registo de sinais concluídos
        "pending_signal": None,
        "results_log": [],

        # Estatísticas por motor/estratégia
        "engine_stats": {
            "seguimento_curto": {"wins": 0, "losses": 0},
            "quebra_controlada": {"wins": 0, "losses": 0},
            "alternancia_chop": {"wins": 0, "losses": 0},
            "equilibrio_frequencia": {"wins": 0, "losses": 0},
            "roadmap_regularidade": {"wins": 0, "losses": 0},
            "protecao_ritmo_t": {"wins": 0, "losses": 0},
        },

        # Estatísticas gerais
        "stats": {
            "wins": 0,
            "wins_by_t": 0,
            "losses": 0,
            "t_hits": 0,
            "entries": 0,
            "observations": 0
        }
    }


# =====================================================
# NORMALIZAÇÃO DE ENTRADAS (P / B / T)
# =====================================================

def parse_token_to_outcome(token):
    t = token.strip().upper()
    # Jogador / Azul -> P
    if t in ("P", "PLAYER", "J", "JOGADOR", "A", "AZUL"):
        return "P"
    # Banca / Vermelho -> B
    if t in ("B", "BANK", "BANKER", "BANCA", "V", "VERMELHO"):
        return "B"
    # Empate / Tie -> T
    if t in ("T", "TIE", "E", "EMPATE", "X"):
        return "T"
    return None


def format_lado_nome(side):
    if side == "P":
        return "P (Jogador / Azul) + T (Empate)"
    if side == "B":
        return "B (Banca / Vermelho) + T (Empate)"
    return "T (Empate)"


def format_cor_curta(side):
    if side == "P":
        return "P (Jogador/Azul)"
    if side == "B":
        return "B (Banca/Vermelho)"
    return "T (Empate)"


# =====================================================
# UTILITÁRIOS DE LEITURA DA MESA E ROADMAPS
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


def calcular_alternancias_seguidas(pb_hist):
    """Conta quantas trocas seguidas (P-B-P-B...) existem no final do histórico P/B."""
    if len(pb_hist) < 2:
        return 0
    trocas = 0
    for i in range(len(pb_hist) - 1, 0, -1):
        if pb_hist[i] != pb_hist[i - 1]:
            trocas += 1
        else:
            break
    return trocas


def construir_colunas_big_road(pb_hist):
    """Agrupa o histórico P/B em colunas verticais estilo Big Road."""
    colunas = []
    for item in pb_hist:
        if not colunas or colunas[-1][0] != item:
            colunas.append([item])
        else:
            colunas[-1].append(item)
    return colunas


def tick_timers(session):
    for side in ("P", "B"):
        if session["cooldown_by_side"][side] > 0:
            session["cooldown_by_side"][side] -= 1
    if session.get("wait_rounds", 0) > 0:
        session["wait_rounds"] -= 1


# =====================================================
# OS 6 MOTORES DE ESTRATÉGIA COM CONCORDÂNCIA E TRAVÃO
# =====================================================

def avaliar_candidato_lado(session, lado):
    """
    Avalia um lado ('P' ou 'B') cruzando todas as famílias de estratégias do Bac Bo:
    1. Seguimento curto de tendência (com trava anti-infinito <= MAX_STREAK_SEGUIR)
    2. Quebra de sequência controlada (apenas em 3 ou 4 seguidos, nunca contra dragon >= 5)
    3. Alternância / Chop (com trava anti-chop infinito <= MAX_CHOP_SEGUIR)
    4. Frequência, equilíbrio e atraso na janela recente
    5. Leitura de Roadmaps (Big Road + regularidade derivada)
    6. Proteção contra excesso de T, cooldown e repetição excessiva do mesmo padrão
    """
    history = session["history"]
    pb_hist = [x for x in history if x in ("P", "B")]
    oposto = "B" if lado == "P" else "P"

    ultimo_pb, streak = calcular_streak_atual(pb_hist)
    trocas_seguidas = calcular_alternancias_seguidas(pb_hist)
    colunas_br = construir_colunas_big_road(pb_hist)

    ult_12_total = history[-12:]
    t_recentes = ult_12_total.count("T")

    ult_12_pb = pb_hist[-12:]
    cont_lado = ult_12_pb.count(lado)
    cont_oposto = ult_12_pb.count(oposto)

    motores_aprovados = []
    tags_padrao = []

    # -------------------------------------------------
    # MOTOR 1: SEGUIMENTO CURTO DE TENDÊNCIA (ANTI-INFINITO)
    # -------------------------------------------------
    # Só acompanha se o lado ganhou 2 ou 3 vezes seguidas. Se já vai em 4+, NÃO segue!
    if ultimo_pb == lado and 2 <= streak <= MAX_STREAK_SEGUIR:
        motores_aprovados.append(
            ("seguimento_curto", f"Tendência curta em {lado} ({streak}/{MAX_STREAK_SEGUIR} máx.)")
        )
        tags_padrao.append("SEG")

    # -------------------------------------------------
    # MOTOR 2: QUEBRA DE SEQUÊNCIA CONTROLADA
    # -------------------------------------------------
    # Só entra contra sequência do oposto se estiver em 3 ou 4 seguidos (evita quebra precoce em 2 e dragon >= 5)
    if ultimo_pb == oposto and 3 <= streak <= MAX_STREAK_QUEBRA:
        motores_aprovados.append(
            ("quebra_controlada", f"Quebra controlada após {streak}x {oposto}")
        )
        tags_padrao.append("QBR")

    # -------------------------------------------------
    # MOTOR 3: ALTERNÂNCIA / CHOP (COM TETO DE SEGURANÇA)
    # -------------------------------------------------
    # Quando a mesa alterna (2 a 4 trocas seguidas), entra no oposto ao último; se >= 5 trocas, trava!
    if ultimo_pb == oposto and 2 <= trocas_seguidas <= MAX_CHOP_SEGUIR:
        motores_aprovados.append(
            ("alternancia_chop", f"Alternância limpa ({trocas_seguidas}/{MAX_CHOP_SEGUIR} trocas)")
        )
        tags_padrao.append("CHOP")

    # -------------------------------------------------
    # MOTOR 4: FREQUÊNCIA, EQUILÍBRIO E DESVIO NA JANELA
    # -------------------------------------------------
    # Evita entrar num lado já hiper-saturado (>= 9/12) e valida equilíbrio ou recuperação saudável
    if (3 <= cont_lado <= 7) or (cont_oposto - cont_lado >= 4 and streak <= 3):
        motores_aprovados.append(
            ("equilibrio_frequencia", f"Janela P/B saudável ({lado}:{cont_lado}/12 vs {oposto}:{cont_oposto}/12)")
        )
        tags_padrao.append("FREQ")

    # -------------------------------------------------
    # MOTOR 5: LEITURA DE ROADMAPS (BIG ROAD + REGULARIDADE)
    # -------------------------------------------------
    # Analisa as últimas 4 colunas do Big Road para confirmar estrutura legível (sem caos total)
    if len(colunas_br) >= 4:
        tamanhos_cols = [len(c) for c in colunas_br[-4:]]
        max_col_recente = max(tamanhos_cols)
        # Estrutura legível: colunas entre 1 e 4 de altura e alinhada com a transição atual
        if max_col_recente <= 4:
            if (len(colunas_br[-1]) >= 2 and colunas_br[-1][0] == lado) or (
                len(colunas_br[-1]) == 1 and colunas_br[-1][0] == oposto and tamanhos_cols[-2] <= 2
            ):
                motores_aprovados.append(
                    ("roadmap_regularidade", f"Big Road estruturado (colunas {tamanhos_cols})")
                )
                tags_padrao.append("ROAD")

    # -------------------------------------------------
    # MOTOR 6: PROTEÇÃO DE RITMO, T E COOLDOWN
    # -------------------------------------------------
    # Valida que não há excesso de T (<= 2 nas últimas 12), sem cooldown no lado e último resultado não foi T
    if (
        t_recentes <= 2
        and history[-1] != "T"
        and session["cooldown_by_side"].get(lado, 0) == 0
    ):
        motores_aprovados.append(
            ("protecao_ritmo_t", f"Mesa limpa (T:{t_recentes}/12, sem cooldown)")
        )
        tags_padrao.append("SAFE")

    padrao_assinatura = "+".join(tags_padrao)

    # Bloqueio adicional: não repetir exatamente o mesmo padrão se já ganhou 2x seguidas com ele
    if (
        padrao_assinatura
        and padrao_assinatura == session.get("last_pattern_used")
        and session.get("consecutive_pattern_wins", 0) >= MAX_CONSEC_WINS_SAME_PATTERN
    ):
        return None

    # Bloqueio adicional: se houver sequência gigante (>= 5) na mesa, não arrisca até estabilizar
    if streak >= 5:
        return None

    if len(motores_aprovados) < MIN_CONCORDANCIA:
        return None

    # Exige também que o Motor 6 (segurança/ritmo) esteja presente na concordância
    engines_ids = [m[0] for m in motores_aprovados]
    if "protecao_ritmo_t" not in engines_ids:
        return None

    score = len(motores_aprovados) - (0.35 * session["side_losses"].get(lado, 0))
    detalhes = " | ".join(m[1] for m in motores_aprovados)

    return {
        "side": lado,
        "engines": engines_ids,
        "pattern": padrao_assinatura,
        "count": len(motores_aprovados),
        "score": score,
        "reason": f"Concordância {len(motores_aprovados)}/6 -> {detalhes}"
    }


def bacbo_sniper_brain(session):
    if session.get("wait_rounds", 0) > 0:
        return None

    history = session["history"]
    pb_hist = [x for x in history if x in ("P", "B")]
    if len(pb_hist) < 10:
        return None

    cand_p = avaliar_candidato_lado(session, "P")
    cand_b = avaliar_candidato_lado(session, "B")

    candidatos = [c for c in (cand_p, cand_b) if c is not None]
    if not candidatos:
        return None

    # Se ambos passarem por algum motivo raro, escolhe apenas o de maior score claro
    if len(candidatos) == 2 and abs(candidatos[0]["score"] - candidatos[1]["score"]) < 0.5:
        return None

    candidatos.sort(key=lambda x: x["score"], reverse=True)
    return candidatos[0]


# =====================================================
# ESTATÍSTICAS E ESTADO DO CÉREBRO
# =====================================================

def wilson_lower_bound(wins, total):
    if total == 0:
        return 0.0
    z = 1.96
    p = wins / total
    denominator = 1 + z * z / total
    center = p + z * z / (2 * total)
    margin = z * sqrt((p * (1 - p) / total) + (z * z / (4 * total * total)))
    return (center - margin) / denominator


def brain_status(session):
    total = len(session["results_log"])
    espera = session.get("wait_rounds", 0)
    estado_espera = f"Pausa obrigatória: {espera} rondas" if espera > 0 else "A filtrar concordância (>=4/6)"
    return (
        "MODO SNIPER SEM GALE (1 COR + T = WIN)",
        f"{total} entradas concluídas | {estado_espera}"
    )


# =====================================================
# RESOLUÇÃO DA ENTRADA ÚNICA (SEM GALE | COR OU T = WIN)
# =====================================================

def process_live_bet(chat_id, session, outcome, raw_label):
    if outcome == "T":
        session["stats"]["t_hits"] += 1

    lado = session["active_side"]
    if lado is None:
        return

    pred = session["pending_signal"]
    session["pending_signal"] = None
    session["active_side"] = None
    session["active_reason"] = ""
    pattern_used = session["active_pattern"]
    session["active_pattern"] = ""

    # REGRA DO UTILIZADOR: VITÓRIA SE SAIR A COR ESCOLHIDA OU SE SAIR T (EMPATE)
    acertou = (outcome == lado) or (outcome == "T")
    session["results_log"].append(acertou)
    session["results_log"] = session["results_log"][-1000:]

    if pred:
        for eng in pred.get("engines", []):
            if eng in session["engine_stats"]:
                if acertou:
                    session["engine_stats"][eng]["wins"] += 1
                else:
                    session["engine_stats"][eng]["losses"] += 1

    if acertou:
        session["stats"]["wins"] += 1
        if outcome == "T":
            session["stats"]["wins_by_t"] += 1
            via_txt = "EMPATE (T) — COBERTURA ACERTADA!"
        else:
            via_txt = f"COR EXATA ({format_cor_curta(lado)})!"

        if pattern_used == session.get("last_pattern_used"):
            session["consecutive_pattern_wins"] += 1
        else:
            session["last_pattern_used"] = pattern_used
            session["consecutive_pattern_wins"] = 1

        if session["side_losses"].get(lado, 0) > 0:
            session["side_losses"][lado] -= 1

        # Pausa obrigatória após GREEN para não disparar entradas seguidas sem necessidade
        session["wait_rounds"] = ESPERA_POS_GREEN

        bot.send_message(
            chat_id,
            "🟢 *GREEN CONFIRMADO (SEM GALE)!* ✨\n\n"
            f"🏆 Resolução: {via_txt}\n"
            f"🎯 Resultado da mesa: `{raw_label}` ({outcome})\n"
            f"🎲 Entrada feita: *{format_lado_nome(lado)}*\n\n"
            f"⏸️ A aguardar pelo menos *{ESPERA_POS_GREEN} rondas* antes de avaliar nova entrada.",
            parse_mode="Markdown"
        )
        return

    # LOSS DIRETO (SEM GALE)
    session["stats"]["losses"] += 1
    session["side_losses"][lado] = session["side_losses"].get(lado, 0) + 1
    session["cooldown_by_side"][lado] = 4
    session["wait_rounds"] = ESPERA_POS_LOSS
    session["consecutive_pattern_wins"] = 0
    session["last_pattern_used"] = ""

    diagnostico = f"Saiu {format_cor_curta(outcome)} contra entrada em {format_lado_nome(lado)}"
    session["error_memory"].append({
        "side": lado,
        "outcome": outcome,
        "pattern": pattern_used,
        "diagnosis": diagnostico
    })
    session["error_memory"] = session["error_memory"][-40:]

    losses = session["stats"]["losses"]
    if losses >= LIMITE_LOSSES:
        session["blocked"] = True
        bot.send_message(
            chat_id,
            "🚨 *LIMITE DE LOSSES ATINGIDO (SEM GALE)!* 🛑\n\n"
            f"🔴 Losses na sessão: {losses}/{LIMITE_LOSSES}\n"
            f"🧠 Diagnóstico: {diagnostico}\n\n"
            "🛑 Sessão bloqueada para proteger a banca.\n"
            "Utiliza /reset para iniciar uma nova sessão.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(
            chat_id,
            "🔴 *LOSS DIRETO (SEM GALE — SEM DOBRAR)*\n\n"
            f"🎯 Resultado da mesa: `{raw_label}` ({outcome})\n"
            f"🔴 Losses na sessão: {losses}/{LIMITE_LOSSES}\n"
            f"🧠 Ajuste: {diagnostico}\n\n"
            f"⏸️ Pausa de *{ESPERA_POS_LOSS} rondas* e lado {lado} arrefecido.",
            parse_mode="Markdown"
        )


# =====================================================
# GERAR NOVA DECISÃO (APENAS QUANDO HÁ ALTA CONCORDÂNCIA)
# =====================================================

def generate_decision(chat_id, session):
    if session["blocked"] or session["active_side"] is not None:
        return

    candidate = bacbo_sniper_brain(session)
    if candidate is None:
        session["stats"]["observations"] += 1
        return

    lado = candidate["side"]
    session["pending_signal"] = candidate
    session["active_side"] = lado
    session["active_reason"] = candidate["reason"]
    session["active_pattern"] = candidate["pattern"]
    session["stats"]["entries"] += 1

    bot.send_message(
        chat_id,
        "🎯 *BAC BO SNIPER — ENTRADA ÚNICA (SEM GALE)*\n\n"
        f"🎲 Entrar em: *{format_lado_nome(lado)}*\n"
        f"💰 Sugestão mão fixa: {APOSTA_COR:.2f}€ na Cor + {APOSTA_T:.2f}€ no T (Empate)\n"
        "🛡️ *SEM GALE* | Saiu a Cor ou saiu *T* = *GREEN*\n\n"
        f"🧩 Padrão: `{candidate['pattern']}`\n"
        f"💡 {candidate['reason']}",
        parse_mode="Markdown"
    )


# =====================================================
# RECEBER NOVA JOGADA
# =====================================================

def receive_result(chat_id, session, outcome, raw_label):
    tick_timers(session)
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
        "🤖 *BAC BO SNIPER BRAIN (ZERO GALE)*\n\n"
        "• *Sem Gale* (mão única, sem perseguir perdas)\n"
        "• *Sempre 1 Cor (`P`/Azul ou `B`/Vermelho) + `T` (Empate)*\n"
        "• *`T` conta como WIN*\n"
        "• *Concordância entre 6 motores de estratégia* + travão anti-sequência infinita\n\n"
        f"📊 Envia as tuas *{JANELA} jogadas iniciais* (`P`, `B` ou `T` — também aceita `V`, `A` ou `E`).\n\n"
        "Exemplo:\n"
        "`P B P P T B P B B P T B`\n\n"
        "/stats - Estatísticas por motor e acerto\n"
        "/status - Estado atual e pausas\n"
        "/reset - Reiniciar sessão\n"
        "/ajuda - Regras do robô",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["ajuda"])
def help_command(message):
    bot.reply_to(
        message,
        "📖 *COMO FUNCIONA ESTE ROBÔ*\n\n"
        f"1. Envia /start e cola {JANELA} resultados iniciais (`P`, `B`, `T` ou `V`, `A`, `E`).\n"
        "2. Depois envia **1 resultado por mensagem**.\n"
        "3. Ele **não usa Gale**: manda sempre 1 Cor + `T`, e tanto a Cor como o `T` dão **GREEN**.\n"
        "4. Nunca segue sequências infinitas (`V V V V V V...`) e faz poucas entradas, apenas quando há concordância real.",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["status"])
def status_command(message):
    session = sessions.get(message.chat.id)
    if session is None:
        bot.reply_to(message, "Utiliza /start primeiro.")
        return

    status, detail = brain_status(session)
    ativa_txt = format_lado_nome(session["active_side"]) if session["active_side"] else "NENHUMA (em observação)"
    ultimo_erro = session["error_memory"][-1]["diagnosis"] if session["error_memory"] else "Nenhum loss registado"

    bot.reply_to(
        message,
        "🧠 *ESTADO DO BAC BO SNIPER*\n\n"
        f"📊 Modo: {status}\n"
        f"🔎 {detail}\n"
        f"📜 Histórico: {len(session['history'])} rondas\n"
        f"⚡ Entrada ativa: {ativa_txt}\n"
        f"🔍 Último loss: {ultimo_erro}\n"
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

    log = session["results_log"]
    recentes = log[-MIN_RECENTES:] if log else []
    taxa_recente = (sum(recentes) / len(recentes) * 100) if recentes else 0.0
    wilson = (wilson_lower_bound(sum(log), len(log)) * 100) if log else 0.0

    engines_txt = ""
    for e_name, e_data in session["engine_stats"].items():
        tot = e_data["wins"] + e_data["losses"]
        rate = (e_data["wins"] / tot * 100) if tot else 0.0
        engines_txt += f"• `{e_name}`: {e_data['wins']}W / {e_data['losses']}L ({rate:.1f}%)\n"

    bot.reply_to(
        message,
        "📊 *RELATÓRIO BAC BO SNIPER (SEM GALE)*\n\n"
        f"🟢 Greens totais: {st['wins']} (via Cor: {st['wins'] - st['wins_by_t']} | via T: {st['wins_by_t']})\n"
        f"🔴 Losses diretos: {st['losses']}/{LIMITE_LOSSES}\n"
        f"🎯 Entradas disparadas: {st['entries']} (Rondas observadas sem entrada: {st['observations']})\n"
        f"📈 Taxa de acerto: {taxa_real:.2f}%\n"
        f"📈 Últimas {MIN_RECENTES}: {taxa_recente:.2f}% | Wilson: {wilson:.2f}%\n\n"
        "*DESEMPENHO POR MOTOR:*\n"
        f"{engines_txt}",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=["reset"])
def reset_command(message):
    sessions[message.chat.id] = nova_sessao()
    bot.reply_to(
        message,
        f"🔄 Sessão reiniciada!\n\nEnvia novamente as {JANELA} jogadas iniciais (`P`, `B` ou `T`).",
        parse_mode="Markdown"
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

    tokens = re.findall(r"\b[PBTEVAXJ]\b", message.text.upper())
    if not tokens:
        bot.reply_to(
            message,
            "⚠️ Formato inválido.\nEnvia P (Jogador/Azul), B (Banca/Vermelho) ou T (Empate)."
        )
        return

    parsed = []
    for tk in tokens:
        outcome = parse_token_to_outcome(tk)
        if outcome is None:
            bot.reply_to(
                message,
                f"⚠️ Valor inválido: `{tk}`.\nUsa P, B ou T (ou V, A, E).",
                parse_mode="Markdown"
            )
            return
        parsed.append((tk, outcome))

    # PRIMEIRO ENVIO: 12 JOGADAS INICIAIS
    if session["awaiting_seed"]:
        if len(parsed) != JANELA:
            bot.reply_to(
                message,
                f"⚠️ Preciso de exatamente {JANELA} jogadas iniciais. Enviaste {len(parsed)}."
            )
            return

        session["history"] = [col for _, col in parsed]
        session["awaiting_seed"] = False

        bot.reply_to(
            message,
            "🧠 *HISTÓRICO INICIAL CARREGADO!* 🚀\n\n"
            f"As {JANELA} jogadas foram analisadas.\n"
            "Envia agora **1 resultado de cada vez** (`P`, `B` ou `T`). O robô só vai mandar entrada quando houver alta concordância.",
            parse_mode="Markdown"
        )
        return

    # FLUXO NORMAL: UMA JOGADA DE CADA VEZ
    if len(parsed) != 1:
        bot.reply_to(
            message,
            "⚠️ Envia apenas um resultado por mensagem (ex: P, B ou T)."
        )
        return

    raw_label, outcome = parsed[0]
    receive_result(chat_id, session, outcome, raw_label)

    if session["active_side"] is None and not session["blocked"]:
        bot.reply_to(
            message,
            f"✅ `{raw_label}` ({outcome}) registado | Histórico: `{len(session['history'])}` | A aguardar concordância segura...",
            parse_mode="Markdown"
        )


# =====================================================
# INICIALIZAÇÃO DO BOT
# =====================================================

if __name__ == "__main__":
    print("BAC BO SNIPER BRAIN (ZERO GALE) ONLINE")

    Thread(
        target=run_web,
        daemon=True
    ).start()

    bot.infinity_polling(
        skip_pending=True,
        timeout=20,
        long_polling_timeout=20
    )
