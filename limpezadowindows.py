#%%

import os
import tkinter as tk
from tkinter import messagebox, ttk, scrolledtext, filedialog
import ctypes
import sys
from datetime import datetime
import shutil
import subprocess
import time
import threading
from ttkthemes import ThemedTk  

# Variável global para o processo de limpeza de disco
processo_limpeza = None
limpeza_cancelada = False

# Verificar permissões de administrador
def verificar_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# Solicitar permissões de administrador
def solicitar_admin():
    if not verificar_admin():
        try:
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
            return True  # Indica que a elevação foi solicitada
        except Exception as e:
            log(f"Erro ao solicitar permissões de administrador: {str(e)}", tipo="ERRO")
            return False
    return True  # Já tem permissões de administrador

# Função para exibir logs na interface e salvar em arquivo
def log(mensagem, tipo="INFO"):
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")  # Formato brasileiro
    mensagem_formatada = f"[{agora}] [{tipo}] {mensagem}\n"

    # Agendar a inserção do log na thread principal
    janela.after(0, lambda: inserir_log(mensagem_formatada, tipo))

def inserir_log(mensagem_formatada, tipo):
    log_text.insert(tk.END, mensagem_formatada)
    log_text.see(tk.END)

    if tipo == "ERRO":
        log_text.tag_add("erro", "end-2c linestart", "end-2c lineend")
        log_text.tag_config("erro", foreground="red")
    elif tipo == "SUCESSO":
        log_text.tag_add("sucesso", "end-2c linestart", "end-2c lineend")
        log_text.tag_config("sucesso", foreground="green")

    with open(log_file_path, "a") as f:
        f.write(mensagem_formatada)

# Função para calcular o tamanho de um arquivo ou diretório
def calcular_tamanho(caminho):
    if os.path.isfile(caminho):
        return os.path.getsize(caminho)
    elif os.path.isdir(caminho):
        tamanho_total = 0
        for raiz, _, arquivos in os.walk(caminho):
            for arquivo in arquivos:
                caminho_arquivo = os.path.join(raiz, arquivo)
                tamanho_total += os.path.getsize(caminho_arquivo)
        return tamanho_total
    return 0

# Função para formatar o espaço liberado em GB ou MB
def formatar_espaco(espaco_bytes):
    if espaco_bytes >= 1024 * 1024 * 1024:  # Se for maior ou igual a 1 GB
        return f"{int(espaco_bytes / (1024 * 1024 * 1024))} GB"  # Arredonda para inteiro
    else:
        return f"{int(espaco_bytes / (1024 * 1024))} MB"  # Arredonda para inteiro

# Função para exibir o relatório de espaço liberado
def exibir_relatorio_espaco_liberado(espaco_liberado):
    espaco_formatado = formatar_espaco(espaco_liberado)
    relatorio = f"Espaço liberado: {espaco_formatado}"
    log(relatorio, tipo="SUCESSO")
    messagebox.showinfo("Relatório de Espaço Liberado", relatorio)

# Função para validar o nome do usuário
def validar_usuario(usuario):
    caminho_usuario = f"C:\\Users\\{usuario}"
    if os.path.exists(caminho_usuario):
        return True
    else:
        log(f"Usuário '{usuario}' não encontrado no sistema.", tipo="ERRO")
        return False

# Função para limpar a Lixeira
def limpar_lixeira():
    global limpeza_cancelada
    if limpeza_cancelada:
        return 0
    try:
        # Calcular o tamanho da lixeira antes de limpar
        tamanho_lixeira = 0
        for raiz, _, arquivos in os.walk("C:\\$Recycle.Bin"):
            for arquivo in arquivos:
                caminho_arquivo = os.path.join(raiz, arquivo)
                tamanho_lixeira += os.path.getsize(caminho_arquivo)

        # Limpar a lixeira
        os.system('PowerShell.exe -NoProfile -Command Clear-RecycleBin -Confirm:$false')

        log(f"Lixeira limpa com sucesso! Espaço liberado: {formatar_espaco(tamanho_lixeira)}", tipo="SUCESSO")
        return tamanho_lixeira
    except Exception as e:
        log(f"Erro ao limpar a Lixeira: {str(e)}", tipo="ERRO")
        return 0

# Função para limpar arquivos temporários do usuário
def limpar_temp_usuarios():
    global limpeza_cancelada
    if limpeza_cancelada:
        return 0
    try:
        usuario = entry_usuario.get()  # Captura o nome do usuário digitado
        if not validar_usuario(usuario):
            return 0

        temp_path = f"C:\\Users\\{usuario}\\AppData\\Local\\Temp"
        if os.path.exists(temp_path):
            espaco_liberado = 0
            excluidos = 0
            nao_excluidos = 0
            for item in os.listdir(temp_path):
                if limpeza_cancelada:
                    return 0
                item_path = os.path.join(temp_path, item)
                try:
                    tamanho_item = calcular_tamanho(item_path)
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                        excluidos += 1
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)  # Ignora erros de permissão
                        excluidos += 1
                    espaco_liberado += tamanho_item
                except Exception as e:
                    if "32" not in str(e) and "5" not in str(e):  # Filtra mensagens de erro [WinError 32] e [WinError 5]
                        log(f"Erro ao excluir {item_path}: {str(e)}", tipo="ERRO")
                        nao_excluidos += 1
            log(f"Arquivos temporários do usuário {usuario} limpos com sucesso! Excluídos: {excluidos}, Não excluídos: {nao_excluidos}", tipo="SUCESSO")
            return espaco_liberado
        else:
            log(f"Diretório temporário do usuário {usuario} não encontrado.", tipo="ERRO")
            return 0
    except Exception as e:
        log(f"Erro ao limpar arquivos temporários: {str(e)}", tipo="ERRO")
        return 0

# Função para limpar cache dos navegadores
def limpar_cache_navegadores():
    global limpeza_cancelada
    if limpeza_cancelada:
        return 0
    try:
        usuario = entry_usuario.get()  # Captura o nome do usuário digitado
        if not validar_usuario(usuario):
            return 0

        # Caminhos dos caches dos navegadores
        navegadores = {
            "Chrome": f"C:\\Users\\{usuario}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Cache",
            "Edge": f"C:\\Users\\{usuario}\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\Cache",
            "Opera GX": f"C:\\Users\\{usuario}\\AppData\\Local\\Opera Software\\Opera GX Stable\\Cache\\Cache_Data",
            "Firefox": f"C:\\Users\\{usuario}\\AppData\\Local\\Mozilla\\Firefox\\Profiles"
        }

        espaco_liberado_total = 0

        # Limpar caches
        for navegador, caminho_cache in navegadores.items():
            if limpeza_cancelada:
                return 0
            if navegador == "Firefox":
                # Encontrar o diretório do perfil do Firefox
                if os.path.exists(caminho_cache):
                    for perfil in os.listdir(caminho_cache):
                        if limpeza_cancelada:
                            return 0
                        if perfil.endswith(".default-release"):  # Filtra apenas perfis ativos
                            cache_firefox = os.path.join(caminho_cache, perfil, "cache2")
                            if os.path.exists(cache_firefox):
                                espaco_liberado = 0
                                excluidos = 0
                                nao_excluidos = 0
                                for item in os.listdir(cache_firefox):
                                    if limpeza_cancelada:
                                        return 0
                                    item_path = os.path.join(cache_firefox, item)
                                    try:
                                        tamanho_item = calcular_tamanho(item_path)
                                        if os.path.isfile(item_path) or os.path.islink(item_path):
                                            os.unlink(item_path)
                                            excluidos += 1
                                        elif os.path.isdir(item_path):
                                            shutil.rmtree(item_path, ignore_errors=True)  # Ignora erros de permissão
                                            excluidos += 1
                                        espaco_liberado += tamanho_item
                                    except Exception as e:
                                        if "32" not in str(e) and "5" not in str(e):  # Filtra mensagens de erro [WinError 32] e [WinError 5]
                                            log(f"Erro ao excluir {item_path}: {str(e)}", tipo="ERRO")
                                            nao_excluidos += 1
                                espaco_liberado_total += espaco_liberado
                                log(f"Cache do Firefox ({perfil}) limpo com sucesso! Excluídos: {excluidos}, Não excluídos: {nao_excluidos}", tipo="SUCESSO")
                            else:
                                log(f"Cache do Firefox ({perfil}) não encontrado.", tipo="ERRO")
                else:
                    log("Diretório de perfis do Firefox não encontrado.", tipo="ERRO")
            else:
                # Limpar caches de outros navegadores
                if os.path.exists(caminho_cache):
                    espaco_liberado = 0
                    excluidos = 0
                    nao_excluidos = 0
                    for item in os.listdir(caminho_cache):
                        if limpeza_cancelada:
                            return 0
                        item_path = os.path.join(caminho_cache, item)
                        try:
                            tamanho_item = calcular_tamanho(item_path)
                            if os.path.isfile(item_path) or os.path.islink(item_path):
                                os.unlink(item_path)
                                excluidos += 1
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path, ignore_errors=True)  # Ignora erros de permissão
                                excluidos += 1
                            espaco_liberado += tamanho_item
                        except Exception as e:
                            if "32" not in str(e) and "5" not in str(e):  # Filtra mensagens de erro [WinError 32] e [WinError 5]
                                log(f"Erro ao excluir {item_path}: {str(e)}", tipo="ERRO")
                                nao_excluidos += 1
                    espaco_liberado_total += espaco_liberado
                    log(f"Cache do {navegador} limpo com sucesso! Excluídos: {excluidos}, Não excluídos: {nao_excluidos}", tipo="SUCESSO")
                else:
                    log(f"Cache do {navegador} não encontrado.", tipo="ERRO")
        return espaco_liberado_total
    except Exception as e:
        log(f"Erro ao limpar cache dos navegadores: {str(e)}", tipo="ERRO")
        return 0

# Função para limpar locais específicos
def limpar_locais_especificos():
    global limpeza_cancelada
    if limpeza_cancelada:
        return 0
    try:
        usuario = entry_usuario.get()  # Captura o nome do usuário digitado
        if not validar_usuario(usuario):
            return 0

        espaco_liberado_total = 0

        # Limpar C:\Windows\Temp
        temp_windows = "C:\\Windows\\Temp"
        if os.path.exists(temp_windows):
            espaco_liberado = 0
            excluidos = 0
            nao_excluidos = 0
            for item in os.listdir(temp_windows):
                if limpeza_cancelada:
                    return 0
                item_path = os.path.join(temp_windows, item)
                try:
                    tamanho_item = calcular_tamanho(item_path)
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                        excluidos += 1
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)  # Ignora erros de permissão
                        excluidos += 1
                    espaco_liberado += tamanho_item
                except Exception as e:
                    if "32" not in str(e) and "5" not in str(e):  # Filtra mensagens de erro [WinError 32] e [WinError 5]
                        log(f"Erro ao excluir {item_path}: {str(e)}", tipo="ERRO")
                        nao_excluidos += 1
            espaco_liberado_total += espaco_liberado
            log(f"C:\\Windows\\Temp limpo com sucesso! Excluídos: {excluidos}, Não excluídos: {nao_excluidos}", tipo="SUCESSO")
        else:
            log("C:\\Windows\\Temp não encontrado.", tipo="ERRO")

        # Limpar C:\Users\{usuario}\AppData\Local\Temp
        temp_usuario = f"C:\\Users\\{usuario}\\AppData\\Local\\Temp"
        if os.path.exists(temp_usuario):
            espaco_liberado = 0
            excluidos = 0
            nao_excluidos = 0
            for item in os.listdir(temp_usuario):
                if limpeza_cancelada:
                    return 0
                item_path = os.path.join(temp_usuario, item)
                try:
                    tamanho_item = calcular_tamanho(item_path)
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                        excluidos += 1
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)  # Ignora erros de permissão
                        excluidos += 1
                    espaco_liberado += tamanho_item
                except Exception as e:
                    if "32" not in str(e) and "5" not in str(e):  # Filtra mensagens de erro [WinError 32] e [WinError 5]
                        log(f"Erro ao excluir {item_path}: {str(e)}", tipo="ERRO")
                        nao_excluidos += 1
            espaco_liberado_total += espaco_liberado
            log(f"C:\\Users\\{usuario}\\AppData\\Local\\Temp limpo com sucesso! Excluídos: {excluidos}, Não excluídos: {nao_excluidos}", tipo="SUCESSO")
        else:
            log(f"C:\\Users\\{usuario}\\AppData\\Local\\Temp não encontrado.", tipo="ERRO")

        # Limpar C:\Users\{usuario}\Recent usando PowerShell com elevação
        recent_usuario = f"C:\\Users\\{usuario}\\Recent"
        if os.path.exists(recent_usuario):
            try:
                espaco_liberado = 0
                for item in os.listdir(recent_usuario):
                    if limpeza_cancelada:
                        return 0
                    item_path = os.path.join(recent_usuario, item)
                    tamanho_item = calcular_tamanho(item_path)
                    espaco_liberado += tamanho_item

                # Usar PowerShell com elevação para limpar o diretório
                comando_powershell = (
                    f'Start-Process PowerShell -ArgumentList "-NoProfile -Command Remove-Item -Path \\"{recent_usuario}\\*\\" -Recurse -Force" -Verb RunAs'
                )
                subprocess.run(comando_powershell, shell=True, check=True)
                espaco_liberado_total += espaco_liberado
                log(f"C:\\Users\\{usuario}\\Recent limpo com sucesso!", tipo="SUCESSO")
            except subprocess.CalledProcessError as e:
                log(f"Erro ao limpar C:\\Users\\{usuario}\\Recent: {str(e)}", tipo="ERRO")
            except Exception as e:
                log(f"Erro ao limpar C:\\Users\\{usuario}\\Recent: {str(e)}", tipo="ERRO")
        else:
            log(f"C:\\Users\\{usuario}\\Recent não encontrado.", tipo="ERRO")

        # Limpar C:\Windows\Prefetch
        prefetch_windows = "C:\\Windows\\Prefetch"
        if os.path.exists(prefetch_windows):
            espaco_liberado = 0
            excluidos = 0
            nao_excluidos = 0
            for item in os.listdir(prefetch_windows):
                if limpeza_cancelada:
                    return 0
                item_path = os.path.join(prefetch_windows, item)
                try:
                    tamanho_item = calcular_tamanho(item_path)
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.unlink(item_path)
                        excluidos += 1
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path, ignore_errors=True)  # Ignora erros de permissão
                        excluidos += 1
                    espaco_liberado += tamanho_item
                except Exception as e:
                    if "32" not in str(e) and "5" not in str(e):  # Filtra mensagens de erro [WinError 32] e [WinError 5]
                        log(f"Erro ao excluir {item_path}: {str(e)}", tipo="ERRO")
                        nao_excluidos += 1
            espaco_liberado_total += espaco_liberado
            log(f"C:\\Windows\\Prefetch limpo com sucesso! Excluídos: {excluidos}, Não excluídos: {nao_excluidos}", tipo="SUCESSO")
        else:
            log("C:\\Windows\\Prefetch não encontrado.", tipo="ERRO")

        return espaco_liberado_total
    except Exception as e:
        log(f"Erro ao limpar locais específicos: {str(e)}", tipo="ERRO")
        return 0

# Função para limpeza de disco usando PowerShell
def limpeza_de_disco():
    global limpeza_cancelada
    if limpeza_cancelada:
        return 0
    try:
        log("Iniciando limpeza de disco... Isso pode levar alguns minutos.", tipo="INFO")
        janela.after(0, lambda: progress_bar.config(mode="indeterminate"))
        janela.after(0, lambda: progress_bar.start())

        # Executa a limpeza de disco usando PowerShell
        comando = (
            'PowerShell.exe -NoProfile -Command '
            'Remove-Item -Path "C:\\Windows\\Temp\\*", "C:\\Windows\\Prefetch\\*" -Recurse -Force; '
            'Clear-RecycleBin -Confirm:$false'
        )
        global processo_limpeza
        processo_limpeza = subprocess.Popen(comando, shell=True)
        processo_limpeza.wait()  # Aguarda o término do processo

        janela.after(0, lambda: progress_bar.stop())
        janela.after(0, lambda: progress_bar.config(mode="determinate"))
        log("Limpeza de disco concluída com sucesso!", tipo="SUCESSO")
        return 0  # Retorna 0 porque o espaço liberado já foi calculado nas funções anteriores
    except Exception as e:
        log(f"Erro ao executar limpeza de disco: {str(e)}", tipo="ERRO")
        return 0

# Função para cancelar a limpeza de disco
def cancelar_limpeza_disco():
    global processo_limpeza, limpeza_cancelada
    limpeza_cancelada = True
    if processo_limpeza:
        processo_limpeza.terminate()
        log("Limpeza de disco cancelada pelo usuário.", tipo="INFO")
        janela.after(0, lambda: progress_bar.stop())
        janela.after(0, lambda: progress_bar.config(mode="determinate"))
        janela.after(0, lambda: botao_executar.config(state=tk.NORMAL))
        janela.after(0, lambda: botao_cancelar.config(state=tk.DISABLED))

# Função para reiniciar o sistema com atraso
def reiniciar_sistema():
    try:
        # Exibir uma mensagem de aviso
        resposta = messagebox.askyesno("Reinicialização", "O sistema será reiniciado em 30 segundos. Deseja continuar?")
        
        if resposta:  # Se o usuário confirmar
            for i in range(30, 0, -1):  # Contagem regressiva de 30 segundos
                label_contagem.config(text=f"Reiniciando em {i} segundos...")
                janela.update()
                time.sleep(1)
            
            # Reiniciar o sistema após a contagem regressiva
            os.system("shutdown /r /t 0")
        else:
            log("Reinicialização cancelada pelo usuário.", tipo="INFO")
    except Exception as e:
        log(f"Erro ao reiniciar o sistema: {str(e)}", tipo="ERRO")

# Função para exibir a ajuda
def mostrar_ajuda():
    ajuda_janela = tk.Toplevel(janela)
    ajuda_janela.title("Ajuda")
    ajuda_janela.geometry("500x400")
    ajuda_janela.configure(bg="#2E3440")

    texto_ajuda = tk.Text(ajuda_janela, wrap="word", width=60, height=20, bg="#3B4252", fg="#D8DEE9", font=("Arial", 10))
    texto_ajuda.pack(pady=10, padx=10, fill="both", expand=True)

    texto_ajuda.insert(tk.END, """
=== Como Usar o Programa de Limpeza de Sistema ===

Este programa foi desenvolvido para ajudar na limpeza de arquivos desnecessários no sistema Windows, 
liberando espaço em disco e melhorando o desempenho do computador. Abaixo estão as funcionalidades 
disponíveis e como utilizá-las:

1. **Limpar Lixeira**:
   - Remove todos os arquivos da Lixeira do Windows.
   - Marque a opção "Limpar Lixeira" para ativar.

2. **Limpar Arquivos Temporários dos Usuários**:
   - Remove arquivos temporários do usuário especificado.
   - Digite o nome do usuário no campo "Nome do Usuário C:" e marque a opção "Limpar Arquivos Temporários dos Usuários".

3. **Limpar Cache dos Navegadores**:
   - Limpa o cache dos navegadores Chrome, Edge, Opera GX e Firefox.
   - Marque a opção "Limpar Cache dos Navegadores".

4. **Limpar Locais Específicos**:
   - Remove arquivos de locais específicos, como:
     - C:\\Windows\\Temp
     - C:\\Users\\{usuário}\\AppData\\Local\\Temp
     - C:\\Users\\{usuário}\\Recent
     - C:\\Windows\\Prefetch
   - Marque a opção "Limpar Locais Específicos".

5. **Limpeza de Disco**:
   - Executa uma limpeza de disco mais abrangente, incluindo a remoção de arquivos temporários do sistema e a Lixeira.
   - Marque a opção "Limpeza de Disco".

6. **Reiniciar a Máquina Após a Limpeza**:
   - Reinicia o computador automaticamente após a conclusão da limpeza.
   - Marque a opção "Reiniciar a máquina após a limpeza".

=== Instruções de Uso ===

1. **Execute o programa como administrador**:
   - Para garantir que todas as funcionalidades funcionem corretamente, execute o programa com permissões de administrador.
   - Se o programa não for executado como administrador, ele solicitará elevação automaticamente.

2. Digite o nome do usuário no campo "Nome do Usuário C:".
3. Marque as opções de limpeza desejadas.
4. Clique em "Executar Limpeza" para iniciar o processo.
5. Acompanhe o progresso na barra de progresso e nos logs exibidos na interface.
6. Se necessário, clique em "Cancelar Limpeza de Disco" para interromper a limpeza de disco.

=== Observações ===

- O programa gera um arquivo de log no Desktop com o nome "limpeza_log.txt".
- Você pode alterar o local do log clicando em "Escolher Local do Log".
- Certifique-se de que o nome do usuário digitado seja válido e exista no sistema.
- A limpeza de disco pode levar alguns minutos, dependendo da quantidade de arquivos a serem removidos.

""")
    texto_ajuda.config(state=tk.DISABLED)  # Impede a edição do texto

# Interface gráfica com Tkinter
def criar_interface():
    global log_text, progress_bar, porcentagem_label, log_file_path, entry_usuario, janela, botao_executar, botao_cancelar, label_contagem

    # Usar ThemedTk para uma interface moderna
    janela = ThemedTk(theme="arc")
    janela.title("Limpeza de Sistema")
    janela.geometry("600x800")
    janela.configure(bg="#2E3440")  # Fundo escuro

    # Definir o caminho do arquivo de log
    log_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "limpeza_log.txt")

    # Título
    titulo = tk.Label(janela, text="Selecione as opções de limpeza:", font=("Arial", 14), bg="#2E3440", fg="#D8DEE9")
    titulo.pack(pady=10)

    # Campo para digitar o nome do usuário
    frame_usuario = tk.Frame(janela, bg="#2E3440")
    frame_usuario.pack(pady=5)

    label_usuario = tk.Label(frame_usuario, text="Nome do Usuário C:", bg="#2E3440", fg="#D8DEE9")
    label_usuario.pack(side=tk.LEFT)

    entry_usuario = tk.Entry(frame_usuario, width=20, bg="#3B4252", fg="#D8DEE9", insertbackground="white")
    entry_usuario.pack(side=tk.LEFT, padx=5)
    entry_usuario.insert(0, "")

    # Checkboxes para seleção
    var_lixeira = tk.BooleanVar()
    var_temp_usuarios = tk.BooleanVar()
    var_cache_navegadores = tk.BooleanVar()
    var_locais_especificos = tk.BooleanVar()
    var_limpeza_disco = tk.BooleanVar()
    var_reiniciar = tk.BooleanVar()

    checkbox_lixeira = tk.Checkbutton(janela, text="Limpar Lixeira", variable=var_lixeira, bg="#2E3440", fg="#D8DEE9", selectcolor="#4C566A")
    checkbox_lixeira.pack(pady=5, anchor="w")

    checkbox_temp_usuarios = tk.Checkbutton(janela, text="Limpar Arquivos Temporários dos Usuários", variable=var_temp_usuarios, bg="#2E3440", fg="#D8DEE9", selectcolor="#4C566A")
    checkbox_temp_usuarios.pack(pady=5, anchor="w")

    checkbox_cache_navegadores = tk.Checkbutton(janela, text="Limpar Cache dos Navegadores", variable=var_cache_navegadores, bg="#2E3440", fg="#D8DEE9", selectcolor="#4C566A")
    checkbox_cache_navegadores.pack(pady=5, anchor="w")

    checkbox_locais_especificos = tk.Checkbutton(janela, text="Limpar Locais Específicos", variable=var_locais_especificos, bg="#2E3440", fg="#D8DEE9", selectcolor="#4C566A")
    checkbox_locais_especificos.pack(pady=5, anchor="w")

    checkbox_limpeza_disco = tk.Checkbutton(janela, text="Limpeza de Disco", variable=var_limpeza_disco, bg="#2E3440", fg="#D8DEE9", selectcolor="#4C566A")
    checkbox_limpeza_disco.pack(pady=5, anchor="w")

    checkbox_reiniciar = tk.Checkbutton(janela, text="Reiniciar a máquina após a limpeza", variable=var_reiniciar, bg="#2E3440", fg="#D8DEE9", selectcolor="#4C566A")
    checkbox_reiniciar.pack(pady=5, anchor="w")

    # Barra de progresso e porcentagem
    progress_frame = tk.Frame(janela, bg="#2E3440")
    progress_frame.pack(pady=10)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Horizontal.TProgressbar", background="#5E81AC", troughcolor="#4C566A")

    progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=400, mode="determinate", style="Horizontal.TProgressbar")
    progress_bar.pack(side=tk.LEFT)

    porcentagem_label = tk.Label(progress_frame, text="0%", bg="#2E3440", fg="#D8DEE9")
    porcentagem_label.pack(side=tk.LEFT, padx=10)

    # Label para contagem regressiva
    label_contagem = tk.Label(janela, text="", font=("Arial", 12), bg="#2E3440", fg="#D8DEE9")
    label_contagem.pack(pady=10)

    # Área de logs
    log_text = scrolledtext.ScrolledText(janela, width=70, height=15, wrap=tk.WORD, bg="#3B4252", fg="#D8DEE9")
    log_text.pack(pady=10)

    # Frame para os botões de log e ajuda
    frame_botoes = tk.Frame(janela, bg="#2E3440")
    frame_botoes.pack(pady=5)

    # Botão para escolher local do log
    def escolher_local_log():
        global log_file_path
        novo_caminho = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Arquivos de Texto", "*.txt")])
        if novo_caminho:
            log_file_path = novo_caminho
            log(f"Local do arquivo de log alterado para: {log_file_path}", tipo="INFO")

    botao_escolher_log = tk.Button(frame_botoes, text="Escolher Local do Log", command=escolher_local_log, bg="#5E81AC", fg="white", relief="flat")
    botao_escolher_log.pack(side=tk.LEFT, padx=5)

    # Botão de ajuda
    botao_ajuda = tk.Button(frame_botoes, text="Ajuda", command=mostrar_ajuda, bg="#5E81AC", fg="white", relief="flat")
    botao_ajuda.pack(side=tk.LEFT, padx=5)

    # Botão de execução
    def executar_limpeza():
        global limpeza_cancelada
        limpeza_cancelada = False
        botao_executar.config(state=tk.DISABLED)
        botao_cancelar.config(state=tk.NORMAL)

        progress_bar["value"] = 0
        porcentagem_label.config(text="0%")
        total_opcoes = sum([var_lixeira.get(), var_temp_usuarios.get(), var_cache_navegadores.get(), var_locais_especificos.get(), var_limpeza_disco.get()])
        if total_opcoes == 0:
            messagebox.showwarning("Aviso", "Nenhuma opção selecionada!")
            botao_executar.config(state=tk.NORMAL)
            botao_cancelar.config(state=tk.DISABLED)
            return

        # Executar a limpeza em uma thread separada
        thread_limpeza = threading.Thread(target=executar_limpeza_em_segundo_plano, args=(total_opcoes,))
        thread_limpeza.start()

    def executar_limpeza_em_segundo_plano(total_opcoes):
        espaco_liberado_total = 0
        progresso = 0

        if var_lixeira.get():
            espaco_liberado_total += limpar_lixeira()
            progresso += 1
            atualizar_barra_progresso(progresso, total_opcoes)

        if var_temp_usuarios.get():
            espaco_liberado_total += limpar_temp_usuarios()
            progresso += 1
            atualizar_barra_progresso(progresso, total_opcoes)

        if var_cache_navegadores.get():
            espaco_liberado_total += limpar_cache_navegadores()
            progresso += 1
            atualizar_barra_progresso(progresso, total_opcoes)

        if var_locais_especificos.get():
            espaco_liberado_total += limpar_locais_especificos()
            progresso += 1
            atualizar_barra_progresso(progresso, total_opcoes)

        if var_limpeza_disco.get():
            espaco_liberado_total += limpeza_de_disco()
            progresso += 1
            atualizar_barra_progresso(progresso, total_opcoes)

        if var_reiniciar.get():
            reiniciar_sistema()

        # Exibir relatório e reabilitar o botão de execução
        janela.after(0, lambda: exibir_relatorio_espaco_liberado(espaco_liberado_total))
        janela.after(0, lambda: messagebox.showinfo("Concluído", "Limpeza concluída!"))
        janela.after(0, lambda: botao_executar.config(state=tk.NORMAL))
        janela.after(0, lambda: botao_cancelar.config(state=tk.DISABLED))

    def atualizar_barra_progresso(progresso, total_opcoes):
        valor_progresso = (progresso / total_opcoes) * 100
        janela.after(0, lambda: progress_bar.config(value=valor_progresso))
        janela.after(0, lambda: porcentagem_label.config(text=f"{int(valor_progresso)}%"))

    botao_executar = tk.Button(janela, text="Executar Limpeza", command=executar_limpeza, bg="#5E81AC", fg="white", font=("Arial", 12), relief="flat")
    botao_executar.pack(pady=20)

    # Botão de cancelamento
    botao_cancelar = tk.Button(janela, text="Cancelar Limpeza de Disco", command=cancelar_limpeza_disco, state=tk.DISABLED, bg="#BF616A", fg="white", relief="flat")
    botao_cancelar.pack(pady=10)

    # Rodar a interface
    janela.mainloop()

# Iniciar a interface
if __name__ == "__main__":
    if not verificar_admin():
        if not solicitar_admin():
            messagebox.showerror("Erro", "Permissões de administrador são necessárias para executar este programa.")
            sys.exit(1)
    criar_interface()