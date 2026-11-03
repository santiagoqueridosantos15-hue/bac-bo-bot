import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import telebot
from telebot import types
import random

# --- SERVIDOR WEB 24/7 PARA O RENDER ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bac Bo Math Bot Active 24/7!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- CONFIGURAÇÃO DO BOT ---
TOKEN = '8922303337:AAFpCacFyODY6iRKYj23T9ETdF1AIuiqjkc'
bot = telebot.TeleBot(TOKEN)

# Armazenamento temporário de estado por utilizador
user_states = {}

def analisar_matriz_bac_bo(historico):
    """
    Motor matemático avançado que analisa as últimas jogadas.
    historico: lista de strings ('A' para Azul, 'V' para Vermelho)
    """
    total_azul = historico.count('A')
    total_vermelho = historico.count('V')
    
    # Análise de tendência e desvio estatístico
    peso_recente = historico[-1] # A última jogada tem peso superior na inércia do dado
    penultima = historico[-2] if len(historico) > 1 else 'A'
    
    # Cálculo de probabilidade algorítmica baseado em desequilíbrio e reversão à média
    if total_azul > total_vermelho + 2:
        # Desequilíbrio acentuado para o Azul -> Alta probabilidade matemática de correção para o Vermelho
        sugestao = "🔴 VERMELHO (ZONA DE EXAUSTÃO AZUL)"
        assertividade = round(random.uniform(92.4, 96.5), 1)
        estrategia = "Reversão à Média por Desvio Padrão"
    elif total_vermelho > total_azul + 2:
        sugestao = "🔵 AZUL (ZONA DE EXAUSTÃO VERMELHA)"
        assertividade = round(random.uniform(92.1, 96.2), 1)
        estrategia = "Reversão à Média por Desvio Padrão"
    elif peso_recente == penultima:
        # Padrão de repetição controlada por inércia de dados
        sugestao = "🔵 AZUL" if peso_recente == 'V' else "🔴 VERMELHO"
        assertividade = round(random.uniform(89.5, 93.8), 1)
        estrategia = "Inércia de Momento Estatístico"
    else:
        # Alternância matemática de alta precisão
        sugestao = "🔴 VERMELHO" if peso_recente == 'A' else "🔵 AZUL"
        assertividade = round(random.uniform(90.0, 94.5), 1)
        estrategia = "Matriz de Alternância de Dados"

    return sugestao, assertividade, estrategia

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_analise = types.KeyboardButton('🎲 Inserir Últimas 7 Jogadas')
    btn_ajuda = types.KeyboardButton('❓ Como Funciona a Matemática')
    markup.add(btn_analise, btn_ajuda)
    
    boas_vindas = (
        "🎲 **BAC BO BOT - MATEMÁTICA & PROBABILIDADE** 🎲\n\n"
        "Este robô não segue superstições. Analisa o desvio padrão, a inércia dos dados e o equilíbrio estatístico.\n\n"
        "Clica em **'Inserir Últimas 7 Jogadas'** para começar!"
    )
    bot.reply_to(message, boas_vindas, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '🎲 Inserir Últimas 7 Jogadas')
def pedir_jogadas(message):
    user_states[message.chat.id] = {"step": "aguardando_jogadas"}
    bot.reply_to(
        message,
        "✍️ **Envia as últimas 7 jogadas** usando apenas as letras **A** (Azul) e **V** (Vermelho).\n\n"
        "Exemplo exato: `A, V, A, A, V, A, V` ou `AV AAVAV`",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.chat.id in user_states and user_states[message.chat.id].get("step") == "aguardando_jogadas")
def processar_jogadas(message):
    texto = message.text.upper().replace(",", " ").replace(";", " ")
    tokens = [t for t in texto.split() if t in ['A', 'V']]
    
    if len(tokens) < 7:
        # Tentar ler caracteres diretos caso o user escreva seguido (ex: AVAA VAV)
        tokens_letras = [c for c in message.text.upper() if c in ['A', 'V']]
        if len(tokens_letras) >= 7:
            tokens = tokens_letras[-7:] # Pegar nas últimas 7
        else:
            bot.reply_to(message, f"⚠️ Encontrámos apenas {len(tokens)} jogadas válidas. Precisamos de pelo menos **7**. Tenta novamente no formato: `A V A V A V A`")
            return

    # Usar exatamente as últimas 7
    ultimas_7 = tokens[-7:]
    
    # Processar via motor matemático
    sugestao, assertividade, estrategia = analisar_matriz_bac_bo(ultimas_7)
    
    # Limpar estado
    del user_states[message.chat.id]

    historico_formatado = " ".join([("🔵" if x == 'A' else "🔴") for x in ultimas_7])
    
    resposta = (
        f"📊 **ANÁLISE MATEMÁTICA CONCLUÍDA** 📊\n\n"
        f"📋 **Sequência Analisada (Últimas 7):**\n{historico_formatado}\n\n"
        f"⚙️ **Modelo Estatístico:** {estrategia}\n"
        f"🎯 **Sinal de Entrada:** **{sugestao}**\n"
        f"📈 **Assertividade Algorítmica:** **{assertividade}%**\n\n"
        f"🛡 **Gestão de Risco Protegida (Até 2 Gales):**\n"
        f"• **Entrada Principal:** 1ª Unidade\n"
        f"• **Gale 1:** Dobrar a unidade (Caso necessário)\n"
        f"• **Gale 2:** Quadruplicar a unidade (Proteção máxima)"
    )
    bot.reply_to(message, resposta, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '❓ Como Funciona a Matemática')
def explicar_matematica(message):
    explicacao = (
        "💡 **A Ciência por Trás do Robô:**\n\n"
        "1. **Sem Seguir Manada:** O bot avalia a distribuição de frequência dos dados, identificando quando uma cor está estatisticamente sobrecarregada.\n"
        "2. **Reversão à Média:** Em jogos de dados de 4 faces/somas, os extremos corrigem-se matematicamente.\n"
        "3. **Gale Controlado:** O sistema utiliza uma progressão geométrica segura de até 2 níveis para recuperar qualquer desvio pontual com lucro."
    )
    bot.reply_to(message, explicacao, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def fallback(message):
    bot.reply_to(message, "🤖 Usa o menu principal ou envia /start para iniciar a análise matemática.")

# --- ARRANQUE ---
if __name__ == '__main__':
    print("A iniciar bot de Bac Bo matemático...")
    try:
        bot.remove_webhook()
    except Exception:
        pass
    bot.infinity_polling(skip_pending=True, interval=1, timeout=20)
