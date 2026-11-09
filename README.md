# conversor-markdown

Converte PDFs em arquivos **Markdown (.md)** para você enviar ao ChatGPT, Claude, Gemini e outras IAs.

## Por que converter?

Quando você envia um PDF, a IA muitas vezes processa cada página também como imagem. Isso gasta muito mais
tokens, enche o limite da conversa mais rápido e aumenta a chance de erro de leitura. Em Markdown, a IA recebe só o
texto, já organizado em títulos, listas e tabelas. Na prática, você consegue mandar mais material de uma vez e as
respostas (resumos, questões, mapas mentais) ficam melhores.

> Gráficos, diagramas e figuras não são convertidos, só o texto. Para apostilas, leis e provas isso costuma ser
> exatamente o que importa.

## Instalação

Requisito: [Python 3.10 ou mais novo](https://www.python.org/downloads/). No Windows, marque a opção
**"Add Python to PATH"** durante a instalação.

```bash
git clone https://github.com/GabriellCabrall/conversor-markdown.git
cd conversor-markdown

# cria um ambiente virtual só para este projeto (não mexe no seu Python)
python -m venv .venv

# ativa o ambiente virtual
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
```

### OCR para PDFs digitalizados (opcional, mas recomendado)

PDFs escaneados (fotos ou digitalizações de páginas) não têm texto "de verdade", só imagem. Para ler esses PDFs, o
conversor usa o **Tesseract OCR**, que é instalado à parte:

- **Windows:** baixe o instalador em <https://github.com/UB-Mannheim/tesseract/wiki>. Durante a instalação, em
  *Additional language data*, marque **Portuguese**. Se preferir o terminal: `winget install UB-Mannheim.TesseractOCR`
  (nesse caso, baixe o [`por.traineddata`](https://github.com/tesseract-ocr/tessdata_best/raw/main/por.traineddata)
  e coloque em `C:\Program Files\Tesseract-OCR\tessdata`).
- **Linux (Debian/Ubuntu):** `sudo apt install tesseract-ocr tesseract-ocr-por`
- **macOS:** `brew install tesseract tesseract-lang`

O conversor encontra o Tesseract sozinho e só aplica OCR nas páginas que precisam.

## Como usar

Com o ambiente virtual ativado:

```bash
python converter.py
```

Uma janela abre para você escolher um ou mais PDFs. O `.md` é salvo na mesma pasta do PDF, com o mesmo nome.

Também dá para passar os arquivos direto:

```bash
python converter.py apostila.pdf
python converter.py aula1.pdf aula2.pdf -o resumos
```

| Opção                 | O que faz                                                          |
|-----------------------|--------------------------------------------------------------------|
| `-o PASTA`            | salva os `.md` em outra pasta                                      |
| `--sem-ocr`           | não usa OCR (mais rápido)                                          |
| `--forcar-ocr`        | aplica OCR em todas as páginas (útil se o texto sair "quebrado")   |
| `--idioma por+eng`    | idioma(s) do OCR (padrão: `por`)                                   |
| `--dpi-ocr 400`       | mais resolução no OCR: mais preciso, porém mais lento              |
| `--manter-cabecalhos` | mantém cabeçalhos e rodapés repetidos (removidos por padrão)       |
| `--separar-paginas`   | insere um separador entre as páginas                               |
| `-y`                  | sobrescreve arquivos `.md` existentes sem perguntar                |

Para ver tudo: `python converter.py --help`

## Dica de uso com a IA

Anexe o `.md` (ou cole o conteúdo) e peça, por exemplo:

> Com base no material anexado, faça um resumo esquematizado para concurso, destacando prazos, exceções e
> pegadinhas comuns de banca. Depois, crie 10 questões de certo/errado no estilo Cebraspe com gabarito comentado.
