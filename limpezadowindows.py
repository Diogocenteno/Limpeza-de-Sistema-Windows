#%% limpezadowindows.py
# -*- coding: utf-8 -*-
"""
Programa de Limpeza e Otimização para Windows

Este script fornece uma interface gráfica para executar diversas tarefas de limpeza
e otimização em sistemas Windows. Requer privilégios de administrador para
funcionar corretamente.
"""

# --- Importações de Módulos Padrão (Não-Gráficos) ---
import subprocess
import sys
import os
import ctypes
import shutil
import threading
import webbrowser
from datetime import datetime
from queue import Queue, Empty

# --- Bloco de Verificação/Instalação de Dependência ---
# Verifica se a biblioteca 'ttkbootstrap' está instalada e, caso não esteja,
# tenta instalá-la automaticamente via pip.
try:
    # A importação real para uso acontecerá somente depois da verificação de administrador.
    import ttkbootstrap
except ImportError:
    print("Biblioteca 'ttkbootstrap' não encontrada. Tentando instalar automaticamente...")
    try:
        # Garante que o pip do ambiente correto seja usado para a instalação.
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ttkbootstrap"])
        # Usa uma caixa de mensagem nativa do Windows para notificar o usuário.
        # Isso evita problemas com a inicialização do Tkinter antes da hora.
        ctypes.windll.user32.MessageBoxW(0, "A dependência 'ttkbootstrap' foi instalada com sucesso. Por favor, execute o programa novamente.", "Instalação Concluída", 0x40) # MB_OK | MB_ICONINFORMATION
        sys.exit(0)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"ERRO CRÍTICO: Falha ao instalar 'ttkbootstrap' via pip. Detalhes: {e}")
        ctypes.windll.user32.MessageBoxW(0, "A biblioteca 'ttkbootstrap' não pôde ser instalada. Por favor, instale-a manualmente ('pip install ttkbootstrap') e tente novamente.", "Erro Crítico", 0x10) # MB_OK | MB_ICONERROR
        sys.exit(1)


# --- Funções de Inicialização ---

def verificar_admin():
    """
    Verifica se o script está sendo executado com privilégios de administrador.

    Returns:
        bool: True se o usuário for administrador, False caso contrário.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        print(f"Não foi possível verificar o status de administrador. Erro: {e}")
        return False

def run_main_app():
    """
    Função principal que importa a GUI e executa a aplicação.

    Esta função só é chamada após a confirmação dos privilégios de administrador,
    evitando erros de inicialização do Tcl/Tk e garantindo que todas as
    operações de sistema terão as permissões necessárias.
    """
    # --- Importações da UI (feitas here para evitar inicialização prematura) ---
    import tkinter as tk
    from tkinter import filedialog
    from tkinter.constants import LEFT, DISABLED, NORMAL, WORD, END
    import ttkbootstrap as ttk
    from ttkbootstrap.scrolled import ScrolledText
    from ttkbootstrap.dialogs import Messagebox

    # --- Classes de Utilidades ---
    class ToolTip:
        """
        Cria uma tooltip (dica de ferramenta) para um widget tkinter.
        Esta classe é autônoma e estilizada para se adequar a temas escuros.
        """
        def __init__(self, widget, text):
            self.widget = widget
            self.text = text
            self.tooltip_window = None
            # Associa os eventos de entrar e sair do mouse com as funções de mostrar/ocultar.
            self.widget.bind("<Enter>", self.show_tooltip)
            self.widget.bind("<Leave>", self.hide_tooltip)

        def show_tooltip(self, event):
            """Exibe a janela da tooltip perto do cursor do mouse."""
            if self.tooltip_window:
                return # Evita criar múltiplas janelas

            # Calcula a posição da tooltip
            x, y, _, _ = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25

            # Cria a janela da tooltip
            self.tooltip_window = tk.Toplevel(self.widget)
            self.tooltip_window.wm_overrideredirect(True) # Remove a barra de título
            self.tooltip_window.wm_geometry(f"+{x}+{y}")

            # Estiliza o label da tooltip
            label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                             background="#404040", foreground="#d0d0d0", relief='solid', borderwidth=1,
                             font=("Arial", "9", "normal"), padx=6, pady=4)
            label.pack(ipadx=1)

        def hide_tooltip(self, event):
            """Destrói a janela da tooltip quando o mouse sai do widget."""
            if self.tooltip_window:
                self.tooltip_window.destroy()
            self.tooltip_window = None

    # --- Classe Principal da Aplicação ---
    class SystemCleanerApp:
        """
        Classe principal para o aplicativo de limpeza e otimização do sistema.
        Encapsula toda a interface gráfica (GUI) e a lógica das funcionalidades.
        """
        def __init__(self, root, style):
            self.root = root
            self.style = style # Armazena o objeto de estilo do ttkbootstrap
            self.processo_limpeza = None # Armazena o subprocesso da limpeza de disco
            self.limpeza_cancelada = False # Flag para controlar o cancelamento
            # Define o caminho padrão para o arquivo de log
            self.log_file_path = os.path.join(os.path.expanduser("~"), "Desktop", "limpeza_log.txt")
            self.log_queue = Queue() # Fila para comunicação entre threads e a GUI
            self.task_buttons = {} # Dicionário para rastrear botões de tarefas
            
            # Inicia a configuração da UI e o processador da fila de logs
            self.setup_ui()
            self.root.after(100, self.process_log_queue)

        def setup_ui(self):
            """Configura a janela principal e todos os widgets da interface gráfica."""
            self.root.title("Limpador e Otimizador para Windows (v1.2)")
            self.root.geometry("750x900")
            self.root.resizable(True, True)
            self.root.minsize(700, 800)

            self.setup_menu()
            
            # Cria o notebook (sistema de abas)
            notebook = ttk.Notebook(self.root, bootstyle="dark")
            notebook.pack(expand=True, fill='both', padx=10, pady=5)

            # Cria as abas
            tab_limpeza = ttk.Frame(notebook, padding=10)
            tab_otimizacao = ttk.Frame(notebook, padding=10)

            notebook.add(tab_limpeza, text='Limpeza Rápida')
            notebook.add(tab_otimizacao, text='Otimização e Reparo do Sistema')

            # Popula cada aba com seus respectivos widgets
            self.setup_limpeza_tab(tab_limpeza)
            self.setup_otimizacao_tab(tab_otimizacao)
            self.setup_log_area()

        def setup_menu(self):
            """Cria e configura o menu superior da aplicação (Arquivo, Ajuda)."""
            menubar = ttk.Menu(self.root)
            self.root.config(menu=menubar)
            
            # Menu "Arquivo"
            file_menu = ttk.Menu(menubar, tearoff=0)
            file_menu.add_command(label="Alterar Local do Arquivo de Log", command=self.escolher_local_log)
            file_menu.add_separator()
            file_menu.add_command(label="Sair", command=self.root.quit)
            menubar.add_cascade(label="Arquivo", menu=file_menu)
            
            # Menu "Ajuda"
            help_menu = ttk.Menu(menubar, tearoff=0)
            help_menu.add_command(label="Sobre e Ajuda", command=self.mostrar_ajuda)
            menubar.add_cascade(label="Ajuda", menu=help_menu)

        def setup_limpeza_tab(self, parent_tab):
            """Cria todos os widgets dentro da aba 'Limpeza'."""
            # --- Seção de Tema ---
            frame_tema = ttk.Frame(parent_tab)
            frame_tema.pack(pady=5, padx=10, fill='x')
            ttk.Label(frame_tema, text="Tema da Interface:").pack(side=LEFT, padx=(0, 5))
            
            self.theme_combobox = ttk.Combobox(
                master=frame_tema,
                state="readonly",
                values=self.style.theme_names()
            )
            self.theme_combobox.pack(side=LEFT, padx=5)
            self.theme_combobox.set(self.style.theme.name)
            self.theme_combobox.bind("<<ComboboxSelected>>", self.change_theme)

            # --- Seção do Usuário ---
            frame_usuario = ttk.Frame(parent_tab)
            frame_usuario.pack(pady=10, padx=10, fill='x')
            ttk.Label(frame_usuario, text="Nome do Usuário do Windows:").pack(side=LEFT, padx=(0, 5))
            self.entry_usuario = ttk.Entry(frame_usuario, width=30)
            self.entry_usuario.pack(side=LEFT, padx=5, expand=True, fill='x')
            try:
                # Tenta preencher automaticamente com o usuário logado
                self.entry_usuario.insert(0, os.getlogin())
            except OSError:
                # Caso falhe, usa um valor padrão
                self.entry_usuario.insert(0, "defaultuser")

            # --- Seção de Opções de Limpeza ---
            frame_opcoes = ttk.Labelframe(parent_tab, text="Opções de Limpeza Rápida", padding=10)
            frame_opcoes.pack(pady=10, padx=10, fill='x')

            self.vars = {
                "lixeira": tk.BooleanVar(), "temp_usuarios": tk.BooleanVar(),
                "cache_navegadores": tk.BooleanVar(), "locais_especificos": tk.BooleanVar(),
                "limpeza_disco": tk.BooleanVar(), "reiniciar": tk.BooleanVar()
            }
            
            tooltip_texts = {
                "lixeira": "Esvazia completamente a Lixeira do Windows.",
                "temp_usuarios": "Apaga arquivos temporários da pasta AppData\\Local\\Temp do usuário.",
                "cache_navegadores": "Remove arquivos de cache do Chrome, Edge e Firefox.",
                "locais_especificos": "Limpa pastas de sistema como C:\\Windows\\Temp e Prefetch.",
                "limpeza_disco": "Abre a ferramenta nativa de Limpeza de Disco do Windows.",
                "reiniciar": "Reinicia o computador automaticamente após a conclusão da limpeza."
            }
            
            opcoes = [
                ("Limpar Lixeira", "lixeira"), ("Limpar Temp dos Usuários", "temp_usuarios"),
                ("Limpar Cache dos Navegadores", "cache_navegadores"), ("Limpar Locais Específicos do Sistema", "locais_especificos"),
                ("Executar Limpeza de Disco (Ferramenta do Windows)", "limpeza_disco"), ("Reiniciar o computador após a limpeza", "reiniciar")
            ]
            
            for texto, var_key in opcoes:
                cb = ttk.Checkbutton(frame_opcoes, text=texto, variable=self.vars[var_key], bootstyle="primary")
                cb.pack(pady=4, anchor="w")
                ToolTip(cb, text=tooltip_texts[var_key])

            # Botões para marcar/desmarcar todas as opções
            select_frame = ttk.Frame(frame_opcoes)
            select_frame.pack(pady=10, fill='x')
            ttk.Button(select_frame, text="Marcar Tudo", command=self.selecionar_todos, bootstyle="secondary").pack(side=LEFT, padx=5)
            ttk.Button(select_frame, text="Desmarcar Tudo", command=self.desmarcar_todos, bootstyle="secondary").pack(side=LEFT, padx=5)

            # --- Seção de Progresso ---
            progress_frame = ttk.Frame(parent_tab)
            progress_frame.pack(pady=10, padx=10, fill='x')
            self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", bootstyle="info-striped")
            self.progress_bar.pack(side=LEFT, expand=True, fill='x')
            self.porcentagem_label = ttk.Label(progress_frame, text="0%")
            self.porcentagem_label.pack(side=LEFT, padx=10)

            # --- Seção de Botões de Ação ---
            frame_botoes = ttk.Frame(parent_tab, padding=10)
            frame_botoes.pack(pady=10, padx=10, fill='x')
            self.botao_executar = ttk.Button(frame_botoes, text="Executar Limpeza", command=self.executar_limpeza_thread, bootstyle="info", padding=10)
            self.botao_executar.pack(side=LEFT, expand=True, fill='x', padx=2)
            self.botao_cancelar = ttk.Button(frame_botoes, text="Cancelar Operação", command=self.cancelar_limpeza, state=DISABLED, bootstyle="danger", padding=10)
            self.botao_cancelar.pack(side=LEFT, expand=True, fill='x', padx=2)

        def setup_otimizacao_tab(self, parent_tab):
            """Cria todos os widgets dentro da aba 'Otimização'."""
            # --- Seção de Desempenho e Conexão ---
            frame_desempenho = ttk.Labelframe(parent_tab, text="Desempenho e Conexão", padding=10)
            frame_desempenho.pack(pady=10, padx=10, fill='x')
            self.create_task_button(frame_desempenho, "Ajustar Plano de Energia para Alto Desempenho", self.ajustar_energia, "ajustar_energia", "Define o plano de energia do Windows para 'Alto Desempenho' para máxima performance.")
            
            # --- Frame específico para a tarefa de desfragmentação ---
            defrag_frame = ttk.Frame(frame_desempenho)
            defrag_frame.pack(pady=5, fill='x', padx=50)

            defrag_button = ttk.Button(
                defrag_frame, 
                text="Desfragmentar Disco", 
                bootstyle="outline-secondary",
                command=lambda: self.run_long_task_in_thread(self.desfragmentar_disco, "desfragmentar_disco")
            )
            defrag_button.pack(side=LEFT, expand=True, fill='x', padx=(0, 10))
            self.task_buttons["desfragmentar_disco"] = defrag_button # Rastreia o botão
            ToolTip(widget=defrag_button, text="Executa a desfragmentação do disco selecionado ao lado. Pode levar muito tempo.")

            available_drives = self.get_available_drives()
            self.drive_combobox = ttk.Combobox(
                defrag_frame, 
                state="readonly", 
                values=available_drives, 
                width=5
            )
            # Define 'C:' como padrão se existir, senão o primeiro da lista
            if 'C:' in available_drives:
                self.drive_combobox.set('C:')
            elif available_drives:
                self.drive_combobox.set(available_drives[0])
            self.drive_combobox.pack(side=LEFT)
            
            # --- Outras ferramentas ---
            btn_teste_conexao = ttk.Button(frame_desempenho, text="Testar Velocidade da Internet", command=self.abrir_teste_conexao, bootstyle="secondary-outline")
            btn_teste_conexao.pack(pady=5, fill='x', padx=50)
            ToolTip(btn_teste_conexao, "Abre o site 'minhaconexao.com.br' para testar sua conexão de internet.")

            # --- Seção de Reparo do Sistema ---
            frame_reparo = ttk.Labelframe(parent_tab, text="Reparo do Sistema (Ferramentas Avançadas)", padding=10)
            frame_reparo.pack(pady=10, padx=10, fill='x')
            self.create_task_button(frame_reparo, "Verificar Arquivos do Sistema (SFC /scannow)", self.executar_sfc, "sfc", "Verifica a integridade de todos os arquivos de sistema protegidos e repara arquivos corrompidos.")
            self.create_task_button(frame_reparo, "Reparar Imagem do Windows (DISM)", self.executar_dism, "dism", "Executa o DISM para reparar a imagem do sistema Windows, que é usada pelo SFC.")
            self.create_task_button(frame_reparo, "Agendar Verificação de Disco (CHKDSK)", self.executar_chkdsk, "chkdsk", "Agenda uma verificação completa do disco C: na próxima reinicialização para corrigir erros.")
            self.create_task_button(frame_reparo, "Corrigir Problemas do Windows Update", self.corrigir_windows_update, "win_update", "Tenta redefinir os componentes do Windows Update para corrigir falhas de atualização.")
            
            btn_protecao = ttk.Button(frame_reparo, text="Abrir Pontos de Restauração do Sistema", command=self.abrir_protecao_sistema, bootstyle="secondary-outline")
            btn_protecao.pack(pady=5, fill='x', padx=50)
            ToolTip(btn_protecao, "Abre a janela de 'Proteção do Sistema' para gerenciar pontos de restauração.")

        def create_task_button(self, parent, text, command, task_id, tooltip_text):
            """
            Cria um botão de tarefa padronizado para a aba de otimização.

            Args:
                parent (tk.Widget): O widget pai onde o botão será colocado.
                text (str): O texto a ser exibido no botão.
                command (callable): A função a ser executada quando o botão é clicado.
                task_id (str): Um identificador único para o botão/tarefa.
                tooltip_text (str): O texto a ser exibido na dica de ferramenta.
            """
            button = ttk.Button(parent, text=text, bootstyle="outline-secondary",
                                command=lambda: self.run_long_task_in_thread(command, task_id))
            button.pack(pady=5, fill='x', padx=50)
            self.task_buttons[task_id] = button
            ToolTip(widget=button, text=tooltip_text)

        def setup_log_area(self):
            """Cria e configura a área de texto para exibir os logs de atividade."""
            log_frame = ttk.Labelframe(self.root, text="Logs de Atividade", padding=10)
            log_frame.pack(pady=10, padx=10, expand=True, fill='both')
            self.log_text = ScrolledText(log_frame, wrap=WORD, font=("Courier New", 9), height=10)
            self.log_text.pack(expand=True, fill='both')
            self.update_log_colors() # Define as cores iniciais das tags de log
            
        def update_log_colors(self):
            """Atualiza as cores das tags de log de acordo com o tema atual."""
            colors = self.style.colors
            self.log_text.tag_config("ERRO", foreground=colors.danger)
            self.log_text.tag_config("SUCESSO", foreground=colors.success)
            self.log_text.tag_config("INFO", foreground=colors.light)
            self.log_text.tag_config("AVISO", foreground=colors.warning)
            self.log_text.tag_config("CMD", foreground=colors.info)

        def change_theme(self, event=None):
            """Altera o tema da aplicação e atualiza as cores dos componentes."""
            selected_theme = self.theme_combobox.get()
            self.style.theme_use(selected_theme)
            self.update_log_colors()
            self.log(f"Tema da interface alterado para '{selected_theme}'.", "INFO")

        def log(self, mensagem, tipo="INFO"):
            """
            Registra uma mensagem na área de log da GUI e no arquivo de log externo.

            Args:
                mensagem (str): A mensagem a ser registrada.
                tipo (str): O tipo da mensagem (INFO, SUCESSO, ERRO, AVISO, CMD).
            """
            agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            mensagem_formatada = f"[{agora}] [{tipo.upper()}] {mensagem}\n"
            
            # A inserção na GUI é agendada para garantir que seja executada na thread principal
            def _inserir_log():
                self.log_text.insert(END, mensagem_formatada, tipo.upper())
                self.log_text.see(END) # Rola automaticamente para o final
            self.root.after(0, _inserir_log)
            
            # Escreve a mesma mensagem no arquivo de log
            try:
                with open(self.log_file_path, "a", encoding='utf-8') as f:
                    f.write(mensagem_formatada)
            except Exception as e:
                # Se a escrita falhar, imprime o erro no console para depuração
                print(f"ERRO: Não foi possível escrever no arquivo de log '{self.log_file_path}'. Detalhes: {e}")

        def process_log_queue(self):
            """
            Processa a fila de mensagens de log vindas de subprocessos em threads.
            Isso permite exibir o output de comandos em tempo real sem travar a GUI.
            """
            try:
                while True: # Processa todas as mensagens atualmente na fila
                    line, tag = self.log_queue.get_nowait()
                    if line: # Adiciona a linha de log na GUI
                        self.log_text.insert(END, line, tag)
                        self.log_text.see(END)
            except Empty:
                pass # A fila está vazia, o que é normal
            finally:
                # Reagenda a verificação da fila para daqui a 100ms
                self.root.after(100, self.process_log_queue)

        def get_user_path(self, *args):
            """
            Monta um caminho de diretório absoluto dentro do perfil do usuário especificado.

            Args:
                *args: Segmentos do caminho a serem juntados (ex: 'AppData', 'Local', 'Temp').

            Returns:
                str | None: O caminho completo ou None se o usuário não for válido.
            """
            user = self.entry_usuario.get().strip()
            if not user:
                self.log("O nome do usuário não pode estar vazio para buscar diretórios.", "ERRO")
                return None
            
            # Constrói o caminho base do perfil do usuário
            user_profile = os.path.join(os.environ.get('SystemDrive', 'C:'), 'Users', user)
            
            if not os.path.exists(user_profile):
                self.log(f"O diretório de perfil para o usuário '{user}' não foi encontrado em '{user_profile}'.", "ERRO")
                return None
                
            return os.path.join(user_profile, *args)

        def limpar_diretorio(self, dir_path, dir_name):
            """
            Apaga de forma segura e recursiva todo o conteúdo de um diretório.

            Args:
                dir_path (str): O caminho completo do diretório a ser limpo.
                dir_name (str): Um nome amigável para o diretório (usado nos logs).

            Returns:
                int: O total de bytes liberados (tamanho dos arquivos e pastas excluídos).
            """
            if self.limpeza_cancelada: return 0
            
            self.log(f"Iniciando limpeza do diretório: '{dir_name}'...", "INFO")
            
            if not dir_path or not os.path.exists(dir_path):
                self.log(f"Diretório '{dir_name}' não encontrado ou caminho inválido. Ignorando.", "AVISO")
                return 0
                
            espaco_liberado, excluidos, falhas = 0, 0, 0
            try:
                for item in os.listdir(dir_path):
                    if self.limpeza_cancelada: break
                    item_path = os.path.join(dir_path, item)
                    try:
                        # Calcula o tamanho antes de deletar
                        tamanho = os.path.getsize(item_path) if os.path.isfile(item_path) else self._get_dir_size(item_path)
                        
                        if os.path.isfile(item_path) or os.path.islink(item_path):
                            os.unlink(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path, ignore_errors=True) # ignore_errors é mais robusto
                            
                        espaco_liberado += tamanho
                        excluidos += 1
                    except Exception:
                        falhas += 1 # Conta falhas em itens individuais
                        
                if falhas > 0:
                    self.log(f"Limpeza de '{dir_name}' concluída com {falhas} falhas. {excluidos} itens excluídos, liberando {self.formatar_espaco(espaco_liberado)}.", "AVISO")
                else:
                    self.log(f"Limpeza de '{dir_name}' concluída. {excluidos} itens excluídos, liberando {self.formatar_espaco(espaco_liberado)}.", "SUCESSO")
            except (PermissionError, FileNotFoundError):
                self.log(f"Acesso negado ou erro ao listar o diretório '{dir_name}'. Pode estar em uso.", "AVISO")
                
            return espaco_liberado

        def _get_dir_size(self, path):
            """Calcula o tamanho total de um diretório e todos os seus subdiretórios."""
            total = 0
            try:
                for dirpath, _, filenames in os.walk(path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if not os.path.islink(fp):
                            total += os.path.getsize(fp)
            except FileNotFoundError:
                return 0 # Diretório pode ter sido removido durante a varredura
            return total
        
        def get_available_drives(self):
            """Retorna uma lista de letras de unidades de disco disponíveis no sistema."""
            drives = []
            for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(f"{letter}:")
            return drives

        # --- Funções de Limpeza Específicas ---

        def limpar_lixeira(self):
            """Esvazia a Lixeira do Windows usando uma chamada da API do sistema."""
            if self.limpeza_cancelada: return 0
            self.log("Iniciando esvaziamento da Lixeira...", "INFO")
            try:
                # SHEmptyRecycleBinW retorna 0 em caso de sucesso
                if ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7) == 0: # 7 = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
                    self.log("Lixeira esvaziada com sucesso.", "SUCESSO")
                else:
                    self.log("Falha ao esvaziar a lixeira ou ela já estava vazia.", "AVISO")
            except Exception as e:
                self.log(f"Erro inesperado ao tentar esvaziar a lixeira. Detalhes: {e}", "ERRO")
            return 0 # Não é prático calcular o espaço liberado por esta operação

        def limpar_temp_usuarios(self):
            """Limpa a pasta de arquivos temporários do usuário."""
            temp_path = self.get_user_path('AppData', 'Local', 'Temp')
            return self.limpar_diretorio(temp_path, "Temp do Usuário")

        def limpar_cache_navegadores(self):
            """Limpa o cache dos principais navegadores (Chrome, Edge, Firefox)."""
            if self.limpeza_cancelada: return 0
            total = 0
            navegadores = {
                "Google Chrome": ('AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
                "Microsoft Edge": ('AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'),
                "Mozilla Firefox": ('AppData', 'Local', 'Mozilla', 'Firefox', 'Profiles')
            }
            for nav, path_parts in navegadores.items():
                if self.limpeza_cancelada: break
                full_path = self.get_user_path(*path_parts)
                if full_path and os.path.exists(full_path):
                    if nav == "Mozilla Firefox":
                        # Firefox armazena o cache dentro de pastas de perfil
                        for profile in os.listdir(full_path):
                            if ".default-release" in profile: # Identifica o perfil principal
                                total += self.limpar_diretorio(os.path.join(full_path, profile, "cache2"), f"Cache do {nav}")
                    else:
                        total += self.limpar_diretorio(full_path, f"Cache do {nav}")
                else:
                    self.log(f"Diretório de cache do {nav} não encontrado. Ignorando.", "INFO")
            return total

        def limpar_locais_especificos(self):
            """Limpa diretórios temporários do sistema, como Windows\Temp e Prefetch."""
            if self.limpeza_cancelada: return 0
            total = 0
            windir = os.environ.get('windir', 'C:\\Windows')
            locais = {
                "Windows Temp": os.path.join(windir, 'Temp'),
                "Prefetch": os.path.join(windir, 'Prefetch'),
            }
            for nome, caminho in locais.items():
                if self.limpeza_cancelada: break
                total += self.limpar_diretorio(caminho, nome)
            return total
            
        def limpeza_de_disco_windows_tool(self):
            """Executa a ferramenta nativa de Limpeza de Disco do Windows."""
            if self.limpeza_cancelada: return 0
            self.log("Iniciando a Limpeza de Disco do Windows... Aguarde a ferramenta ser fechada.", "INFO")
            self.log("Nota: As opções desta ferramenta devem ser pré-configuradas executando 'cleanmgr.exe /sageset:1' manualmente no terminal.", "AVISO")
            try:
                # O comando 'sagerun:1' executa a limpeza com as opções previamente salvas via 'sageset:1'
                self.processo_limpeza = subprocess.Popen('cleanmgr.exe /sagerun:1', shell=True)
                self.processo_limpeza.wait() # Aguarda o processo terminar
                if not self.limpeza_cancelada:
                    self.log("Ferramenta de Limpeza de Disco do Windows foi fechada.", "SUCESSO")
            except Exception as e:
                if not self.limpeza_cancelada:
                    self.log(f"Erro ao executar a Limpeza de Disco do Windows. Detalhes: {e}", "ERRO")
            finally:
                self.processo_limpeza = None
            return 0

        # --- Funções de Otimização e Reparo ---

        def run_long_task_in_thread(self, task_function, task_id):
            """
            Inicia uma tarefa de longa duração em uma nova thread para não travar a GUI.

            Args:
                task_function (callable): A função da tarefa a ser executada.
                task_id (str): O ID da tarefa, usado para controlar o estado do botão.
            """
            button = self.task_buttons.get(task_id)
            if button and button['state'] == DISABLED:
                self.log("Uma tarefa de otimização já está em execução. Por favor, aguarde a sua conclusão.", "AVISO")
                return
            
            # Inicia a função alvo em uma thread daemon (que não impede o programa de fechar)
            threading.Thread(target=task_function, args=(task_id,), daemon=True).start()

        def set_task_button_state(self, task_id, state):
            """Altera o estado (ativado/desativado) de um botão de tarefa."""
            button = self.task_buttons.get(task_id)
            if button:
                button.config(state=state)

        def _stream_process_output(self, process):
            """Lê o output de um subprocesso linha por linha e o envia para a fila de logs."""
            try:
                # Itera sobre o stdout do processo até que ele termine
                for line in iter(process.stdout.readline, ''):
                    self.log_queue.put((line, "CMD"))
                process.stdout.close()
            except Exception as e:
                self.log_queue.put((f"Erro ao ler o output do processo. Detalhes: {e}\n", "ERRO"))

        def run_command_with_stream(self, command, task_id, start_msg, success_msg, error_msg):
            """
            Executa um comando do sistema, captura seu output em tempo real e atualiza a GUI.

            Args:
                command (list|str): O comando e seus argumentos.
                task_id (str): O ID da tarefa para controle do botão.
                start_msg (str): Mensagem de log para o início da tarefa.
                success_msg (str): Mensagem de log para o sucesso da tarefa.
                error_msg (str): Mensagem de log para a falha da tarefa.
            """
            self.root.after(0, lambda: self.set_task_button_state(task_id, DISABLED))
            self.log(start_msg, "INFO")
            
            try:
                use_shell = isinstance(command, str)

                process = subprocess.Popen(
                    command,
                    shell=use_shell, 
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, # Redireciona stderr para stdout
                    text=True, encoding='cp850', errors='ignore', # cp850 é o encoding do cmd do Windows
                    creationflags=subprocess.CREATE_NO_WINDOW, # Não cria uma janela de console
                    bufsize=1 # Line-buffered
                )
                
                # Inicia uma thread para ler o output do processo
                threading.Thread(target=self._stream_process_output, args=(process,), daemon=True).start()

                # Função para verificar periodicamente se o processo terminou
                def check_completion():
                    if process.poll() is not None: # Processo terminou
                        if process.returncode == 0:
                            self.log(success_msg, "SUCESSO")
                        else:
                            self.log(f"{error_msg}. Código de saída: {process.returncode}", "ERRO")
                        self.root.after(0, lambda: self.set_task_button_state(task_id, NORMAL))
                    else:
                        # Se não terminou, verifica novamente em 200ms
                        self.root.after(200, check_completion)
                
                self.root.after(200, check_completion)
            except Exception as e:
                self.log(f"Falha crítica ao tentar iniciar a tarefa '{task_id}'. Detalhes: {e}", "ERRO")
                self.root.after(0, lambda: self.set_task_button_state(task_id, NORMAL))

        def ajustar_energia(self, task_id):
            """Define o plano de energia do Windows como 'Alto Desempenho'."""
            # GUID padrão para o plano de Alto Desempenho
            guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
            self.run_command_with_stream(
                f"powercfg /setactive {guid}", task_id, 
                "Ativando o plano de energia 'Alto Desempenho'...", 
                "Plano de energia alterado para 'Alto Desempenho' com sucesso.", 
                "Falha ao alterar o plano de energia."
            )

        def desfragmentar_disco(self, task_id):
            """Executa o desfragmentador de disco do Windows no disco selecionado."""
            selected_drive = self.drive_combobox.get()
            if not selected_drive:
                self.log("Nenhum disco selecionado para desfragmentação.", "ERRO")
                return
            
            command = ['defrag', selected_drive, '/U', '/V'] # /U: progresso, /V: verbose
            self.run_command_with_stream(
                command, task_id,
                f"Iniciando desfragmentação do disco {selected_drive}... Isso pode levar muito tempo.",
                f"Desfragmentação do disco {selected_drive} concluída com sucesso.",
                f"Ocorreu um erro durante a desfragmentação do disco {selected_drive}."
            )

        def executar_sfc(self, task_id):
            """Executa o Verificador de Arquivos de Sistema (SFC)."""
            self.run_command_with_stream(
                ['sfc', '/scannow'], task_id,
                "Iniciando verificação SFC /scannow... Isso pode levar vários minutos.",
                "Verificação SFC concluída. Verifique o log acima para detalhes.",
                "Erro ao executar o SFC."
            )
            
        def executar_dism(self, task_id):
            """Executa o DISM para reparar a imagem do sistema."""
            self.run_command_with_stream(
                ['DISM', '/Online', '/Cleanup-Image', '/RestoreHealth'], task_id,
                "Iniciando DISM /Online /Cleanup-Image /RestoreHealth... Isso pode demorar bastante.",
                "Operação DISM concluída. Verifique o log acima para detalhes.",
                "Erro ao executar o DISM."
            )
            
        def executar_chkdsk(self, task_id):
            """Agenda a verificação de disco (CHKDSK) para a próxima reinicialização."""
            self.set_task_button_state(task_id, DISABLED) # Desativa o botão imediatamente
            if Messagebox.yesno("Isso agendará uma verificação do disco C: na próxima vez que o computador for ligado. Deseja continuar?", "Confirmar Agendamento do CHKDSK") == "Yes":
                self.run_command_with_stream(
                    ['fsutil', 'dirty', 'set', 'C:'], task_id,
                    "Agendando verificação de disco (CHKDSK) para a unidade C:...",
                    "CHKDSK agendado com sucesso para a próxima reinicialização.",
                    "Falha ao agendar o CHKDSK."
                )
            else:
                self.log("Agendamento do CHKDSK cancelado pelo usuário.", "INFO")
                self.root.after(0, lambda: self.set_task_button_state(task_id, NORMAL))
        
        def corrigir_windows_update(self, task_id):
            """Executa uma sequência de comandos para tentar corrigir o Windows Update."""
            if Messagebox.yesno("Isso irá parar os serviços do Windows Update, renomear a pasta de distribuição e reiniciar os serviços. É um procedimento seguro, mas confirme para continuar.", "Confirmar Reparo do Windows Update") != "Yes":
                self.log("Reparo do Windows Update cancelado pelo usuário.", "INFO")
                return
            
            # A execução é feita em uma thread para não travar a GUI
            def run_in_thread():
                self.root.after(0, lambda: self.set_task_button_state(task_id, DISABLED))
                self.log("Iniciando reparo dos componentes do Windows Update...", "INFO")
                
                commands = [
                    ("net stop wuauserv", "Parando o serviço do Windows Update (wuauserv)..."),
                    ("net stop bits", "Parando o Serviço de Transferência Inteligente (BITS)..."),
                    (f"ren \"{os.path.join(os.environ['windir'], 'SoftwareDistribution')}\" SoftwareDistribution.old", "Renomeando a pasta de distribuição de software..."),
                    ("net start wuauserv", "Iniciando o serviço do Windows Update (wuauserv)..."),
                    ("net start bits", "Iniciando o Serviço de Transferência Inteligente (BITS)...")
                ]
                
                success = True
                for cmd, msg in commands:
                    self.log(msg, "INFO")
                    try:
                        # Usamos subprocess.run aqui por ser mais simples para comandos sequenciais
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
                        # Ignora erros se o serviço já estiver parado
                        if result.returncode != 0 and not any(err in result.stderr.lower() for err in ["não foi iniciado", "not started", "already been stopped"]):
                            self.log(f"Falha na execução do comando '{cmd}'. Detalhes: {result.stderr.strip()}", "ERRO")
                            success = False; break
                    except Exception as e:
                        self.log(f"Erro crítico ao executar o comando '{cmd}'. Detalhes: {e}", "ERRO")
                        success = False; break
                        
                if success:
                    self.log("Reparo do Windows Update concluído com sucesso!", "SUCESSO")
                else:
                    self.log("O processo de reparo do Windows Update encontrou um erro e foi interrompido.", "ERRO")
                
                self.root.after(0, lambda: self.set_task_button_state(task_id, NORMAL))

            threading.Thread(target=run_in_thread, daemon=True).start()

        # --- Funções Auxiliares e de UI ---

        def abrir_protecao_sistema(self):
            """Abre a janela de propriedades de Proteção do Sistema do Windows."""
            self.log("Abrindo a janela de Proteção do Sistema...", "INFO")
            try:
                subprocess.Popen("SystemPropertiesProtection.exe", shell=True)
            except Exception as e:
                self.log(f"Não foi possível abrir a Proteção do Sistema. Detalhes: {e}", "ERRO")

        def abrir_teste_conexao(self):
            """Abre um site de teste de velocidade de internet no navegador padrão."""
            url = "https://www.minhaconexao.com.br/"
            self.log(f"Abrindo site para teste de conexão: {url}", "INFO")
            try:
                webbrowser.open(url)
            except Exception as e:
                self.log(f"Não foi possível abrir o link no navegador. Detalhes: {e}", "ERRO")

        def selecionar_todos(self):
            """Marca todas as caixas de seleção de limpeza, exceto a de reiniciar."""
            for key, var in self.vars.items():
                if key != 'reiniciar':
                    var.set(True)

        def desmarcar_todos(self):
            """Desmarca todas as caixas de seleção de limpeza."""
            for var in self.vars.values():
                var.set(False)

        def executar_limpeza_thread(self):
            """Prepara e inicia o processo de limpeza em uma nova thread."""
            if not self.entry_usuario.get().strip():
                Messagebox.show_warning("O nome do usuário é obrigatório para continuar.", "Aviso: Usuário Inválido")
                return
            if not any(v.get() for v in self.vars.values()):
                Messagebox.show_warning("Nenhuma opção de limpeza foi selecionada!", "Aviso: Nenhuma Seleção")
                return

            # Configura o estado da UI para o modo de limpeza
            self.limpeza_cancelada = False
            self.botao_executar.config(state=DISABLED)
            self.botao_cancelar.config(state=NORMAL)
            
            # Reseta a barra de progresso
            self.progress_bar.stop()
            self.progress_bar.config(mode='determinate')
            self.progress_bar["value"] = 0
            self.porcentagem_label.config(text="0%")
            
            # Limpa a área de log e marca o início
            self.log_text.delete('1.0', END)
            self.log("--- INÍCIO DA ROTINA DE LIMPEZA ---", "INFO")
            
            total_opcoes = sum(v.get() for k, v in self.vars.items() if k != 'reiniciar')
            threading.Thread(target=self.executar_limpeza_em_background, args=(total_opcoes,), daemon=True).start()

        def executar_limpeza_em_background(self, total_opcoes):
            """
            Executa a sequência de tarefas de limpeza selecionadas.
            Esta função é executada em uma thread separada.
            """
            espaco_liberado_total = 0
            progresso = 0
            tarefas = {
                "lixeira": self.limpar_lixeira, "temp_usuarios": self.limpar_temp_usuarios,
                "cache_navegadores": self.limpar_cache_navegadores, "locais_especificos": self.limpar_locais_especificos,
                "limpeza_disco": self.limpeza_de_disco_windows_tool,
            }
            
            for key, func in tarefas.items():
                if self.limpeza_cancelada:
                    self.log("Operação de limpeza cancelada pelo usuário.", "AVISO")
                    break
                
                if self.vars[key].get():
                    espaco_liberado_total += func()
                    progresso += 1
                    self.atualizar_barra_progresso(progresso, total_opcoes)
            
            # Função para ser executada na thread principal ao final da limpeza
            def finalizacao_gui():
                self.progress_bar.stop()

                if self.limpeza_cancelada:
                    self.log("Limpeza interrompida. Revertendo estado da interface.", "AVISO")
                    self.progress_bar["value"] = 0
                    self.porcentagem_label.config(text="Cancelado")
                else:
                    # Garante que a barra de progresso chegue a 100%
                    if total_opcoes > 0:
                        self.progress_bar["value"] = 100
                        self.porcentagem_label.config(text="100%")

                    relatorio = f"Espaço total liberado (estimado): {self.formatar_espaco(espaco_liberado_total)}"
                    self.log("--- ROTINA DE LIMPEZA CONCLUÍDA ---", "INFO")
                    self.log(relatorio, "SUCESSO")
                    Messagebox.show_info(f"Limpeza finalizada com sucesso!\n{relatorio}", "Concluído")
                
                # Verifica se deve reiniciar o sistema
                if self.vars['reiniciar'].get() and not self.limpeza_cancelada:
                    self.reiniciar_sistema()

                # Restaura o estado dos botões
                self.botao_executar.config(state=NORMAL)
                self.botao_cancelar.config(state=DISABLED)

            self.root.after(0, finalizacao_gui)

        def cancelar_limpeza(self):
            """Sinaliza o cancelamento da limpeza e tenta parar processos externos."""
            self.limpeza_cancelada = True
            if self.processo_limpeza: # Se a limpeza de disco estiver rodando
                try:
                    self.processo_limpeza.terminate()
                except Exception as e:
                    self.log(f"Não foi possível terminar o processo de limpeza de disco. Detalhes: {e}", "ERRO")
            
            self.log("Cancelamento solicitado. A operação será interrompida na próxima etapa.", "AVISO")
            self.botao_cancelar.config(state=DISABLED)

        def atualizar_barra_progresso(self, progresso, total):
            """Atualiza o valor da barra de progresso e o rótulo de porcentagem."""
            if total > 0:
                valor = (progresso / total) * 100
                # Usa 'after' para garantir que a atualização da GUI ocorra na thread principal
                self.root.after(0, lambda: self.progress_bar.config(value=valor))
                self.root.after(0, lambda: self.porcentagem_label.config(text=f"{int(valor)}%"))

        def escolher_local_log(self):
            """Abre uma caixa de diálogo para o usuário escolher onde salvar o log."""
            novo_caminho = filedialog.asksaveasfilename(
                defaultextension=".txt", 
                filetypes=[("Arquivos de Texto", "*.txt")], 
                initialfile="limpeza_log.txt",
                title="Escolha o local para salvar o arquivo de log"
            )
            if novo_caminho:
                self.log_file_path = novo_caminho
                self.log(f"O local do arquivo de log foi alterado para: {self.log_file_path}", "INFO")

        @staticmethod
        def formatar_espaco(b):
            """Converte um valor em bytes para um formato legível (KB, MB, GB)."""
            if b < 1024: return f"{b} B"
            if b < 1024**2: return f"{b/1024:.2f} KB"
            if b < 1024**3: return f"{b/1024**2:.2f} MB"
            return f"{b/1024**3:.2f} GB"

        def reiniciar_sistema(self):
            """Exibe uma confirmação e, se aceita, reinicia o computador."""
            self.log("A opção de reiniciar após a limpeza foi selecionada.", "AVISO")
            if Messagebox.yesno("O sistema será reiniciado em 1 minuto para completar a limpeza. Salve todo o seu trabalho. Deseja continuar?", "Confirmar Reinicialização", alert=True) == "Yes":
                self.log("COMANDO DE REINICIALIZAÇÃO ENVIADO.", "AVISO")
                os.system("shutdown /r /t 60") # /r = restart, /t 60 = em 60 segundos
            else:
                self.log("Reinicialização cancelada pelo usuário.", "INFO")
        
        @staticmethod
        def mostrar_ajuda():
            """Exibe uma caixa de diálogo com informações de ajuda sobre o programa."""
            ajuda_texto = """
            Limpador e Otimizador para Windows

            Aba 'Limpeza Rápida':
            - Selecione as áreas do sistema que deseja limpar.
            - Insira o nome de usuário do Windows para limpar pastas específicas do perfil.
            - Clique em 'Executar Limpeza' para iniciar. É recomendado fechar os navegadores antes de limpar o cache.

            Aba 'Otimização e Reparo':
            - Contém ferramentas avançadas para diagnóstico e reparo do sistema.
            - Passe o mouse sobre cada botão para ver uma descrição detalhada da sua função.
            - Tarefas como SFC e DISM podem levar muito tempo para serem concluídas e não devem ser interrompidas.

            Logs:
            - Todas as ações são registradas na área de 'Logs de Atividade' e salvas em um arquivo de texto na sua Área de Trabalho.

            Permissões:
            - Este programa requer permissões de Administrador para acessar áreas protegidas do sistema e executar comandos de reparo.
            """
            Messagebox.show_info(ajuda_texto, "Ajuda e Sobre")

    # --- Ponto de Entrada da Aplicação Gráfica ---
    # A inicialização da GUI é feita aqui dentro para garantir que o 'ttk' já foi importado.
    
    # Cria o motor de estilos primeiro, que também cria uma janela raiz de forma segura.
    style = ttk.Style(theme='cyborg')
    # Pega a janela raiz criada pelo motor de estilos.
    root = style.master
    # Cria a instância da aplicação, passando a janela e o motor de estilos.
    app = SystemCleanerApp(root, style)
    # Inicia o loop principal da aplicação gráfica.
    root.mainloop()


# --- Ponto de Entrada Principal do Script ---
if __name__ == "__main__":
    # 1. Verifica se o script já tem permissões de administrador.
    if not verificar_admin():
        # 2. Se não tiver, exibe uma mensagem e tenta se re-executar como administrador.
        ctypes.windll.user32.MessageBoxW(0, "Este programa precisa de permissões de administrador para funcionar. Ele será reiniciado para solicitar a elevação.", "Permissões Necessárias", 0x30) # MB_OK | MB_ICONWARNING
        try:
            # Tenta re-lançar o script com o verbo "runas", que solicita elevação de privilégios (UAC).
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        except Exception as e:
            # Caso a elevação falhe.
            ctypes.windll.user32.MessageBoxW(0, f"Não foi possível solicitar permissões de administrador automaticamente.\nPor favor, clique com o botão direito no arquivo e selecione 'Executar como administrador'.\n\nErro: {e}", "Erro de Elevação", 0x10) # MB_OK | MB_ICONERROR
            sys.exit(1)
        # Sai do processo atual, não-elevado.
        sys.exit(0)
    
    # 3. Se o script já tem permissão de admin, a aplicação principal é iniciada.
    # A chamada para run_main_app() cuida de todas as importações e inicializações da GUI.
    run_main_app()
