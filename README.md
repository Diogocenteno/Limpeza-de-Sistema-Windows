🧹 Limpeza de Sistema Windows
Aplicativo em Python com interface gráfica (Tkinter + ttk themes) para realizar limpeza de arquivos desnecessários no Windows, liberar espaço em disco e melhorar o desempenho.
<img width="1900" height="952" alt="Captura de tela 2025-09-03 111853" src="https://github.com/user-attachments/assets/c42f914b-50f2-48bc-a1cf-85b88687f428" />



🔧 Funcionalidades
Limpeza de:

Lixeira

Arquivos temporários do usuário

Cache dos navegadores (Chrome, Edge, Opera GX, Firefox)

Pastas específicas do sistema (Temp, Prefetch, Recent, etc.)

Disco com comandos PowerShell

Interface com:

Barra de progresso

Logs coloridos

Opção de reinício automático

Escolha do local de log

Ajuda integrada

🚀 Requisitos
Python 3.8+

Windows

Acesso de administrador

Bibliotecas:

ttkthemes

tkinter (nativo do Python)

▶️ Como executar
Instale as dependências:

pip install ttkthemes
Execute o script com permissões de administrador:

python limpezadowindows.py
Se não estiver em modo administrador, o script solicitará a elevação automaticamente.

📂 Estrutura de Log
Gera automaticamente um limpeza_log.txt na área de trabalho com todas as ações realizadas.

⚠️ Observações
Execute como administrador.

Certifique-se de digitar o nome de usuário corretamente.

Alguns arquivos exigem permissões avançadas — erros são logados.

A limpeza pode levar alguns minutos dependendo do volume de arquivos.

No terminal coloque pyinstaller --onefile --windowed limpezadowindows.py para gerar o APP
