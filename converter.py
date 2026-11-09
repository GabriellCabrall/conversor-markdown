"""
Conversor de PDF para Markdown.

Converte PDFs em arquivos .md, prontos para enviar a IAs generativas
(ChatGPT, Claude, Gemini...). Páginas digitalizadas (imagens de texto)
são lidas com OCR via Tesseract, se ele estiver instalado.

Uso:
    python converter.py                      # abre janela para escolher os PDFs
    python converter.py arquivo.pdf          # converte um arquivo
    python converter.py *.pdf -o resumos/    # vários arquivos, saída em outra pasta
    python converter.py --help               # todas as opções
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Garante acentuação correta no terminal do Windows.
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# Pastas onde o instalador do Tesseract costuma colocar os idiomas no Windows.
PASTAS_TESSDATA_WINDOWS = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR" / "tessdata",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Tesseract-OCR" / "tessdata",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tessdata",
]


# --------------------------------------------------------------------------
# Tesseract (OCR)
# --------------------------------------------------------------------------

def localizar_tessdata() -> Path | None:
    """Encontra a pasta de idiomas do Tesseract e configura TESSDATA_PREFIX."""
    atual = os.environ.get("TESSDATA_PREFIX")
    if atual and Path(atual).is_dir():
        return Path(atual)

    candidatas = list(PASTAS_TESSDATA_WINDOWS) if sys.platform == "win32" else []
    candidatas += [
        Path("/usr/share/tesseract-ocr/5/tessdata"),
        Path("/usr/share/tesseract-ocr/4.00/tessdata"),
        Path("/usr/share/tessdata"),
        Path("/opt/homebrew/share/tessdata"),
        Path("/usr/local/share/tessdata"),
    ]
    for pasta in candidatas:
        if pasta.is_dir():
            os.environ["TESSDATA_PREFIX"] = str(pasta)
            return pasta

    # Último recurso: deixa o PyMuPDF procurar o tesseract no PATH.
    try:
        import pymupdf

        pasta = pymupdf.get_tessdata()
        if pasta and Path(pasta).is_dir():
            os.environ["TESSDATA_PREFIX"] = str(pasta)
            return Path(pasta)
    except Exception:
        pass
    return None


def idiomas_disponiveis(tessdata: Path) -> set[str]:
    return {p.stem for p in tessdata.glob("*.traineddata")}


def preparar_ocr(idioma: str) -> tuple[bool, str]:
    """Verifica se o OCR pode ser usado. Retorna (disponivel, idioma_final)."""
    tessdata = localizar_tessdata()
    if tessdata is None:
        print(
            "AVISO: Tesseract não encontrado. PDFs digitalizados (páginas que são\n"
            "       imagens) sairão sem texto. Veja no README como instalar.\n"
        )
        return False, idioma

    instalados = idiomas_disponiveis(tessdata)
    pedidos = idioma.split("+")
    faltando = [i for i in pedidos if i not in instalados]
    if faltando:
        restantes = [i for i in pedidos if i in instalados]
        print(
            f"AVISO: idioma(s) de OCR não instalado(s): {', '.join(faltando)}.\n"
            f"       Instalados: {', '.join(sorted(instalados)) or 'nenhum'}.\n"
            "       Sem o português ('por') o OCR perde acentos. Veja o README.\n"
        )
        if not restantes:
            if "eng" in instalados:
                restantes = ["eng"]
            else:
                return False, idioma
        idioma = "+".join(restantes)
    return True, idioma


# --------------------------------------------------------------------------
# Seleção de arquivos
# --------------------------------------------------------------------------

def escolher_pdfs_na_janela() -> list[Path]:
    """Abre a janela padrão do sistema para escolher um ou mais PDFs."""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return escolher_pdfs_no_terminal()

    raiz = tk.Tk()
    raiz.withdraw()
    raiz.attributes("-topmost", True)  # janela aparece na frente do terminal
    caminhos = filedialog.askopenfilenames(
        title="Escolha o(s) PDF(s) para converter",
        filetypes=[("Arquivos PDF", "*.pdf"), ("Todos os arquivos", "*.*")],
    )
    raiz.destroy()
    return [Path(c) for c in caminhos]


def escolher_pdfs_no_terminal() -> list[Path]:
    entrada = input("Caminho do PDF (pode arrastar o arquivo para cá): ").strip()
    entrada = entrada.strip('"').strip("'")
    return [Path(entrada)] if entrada else []


# --------------------------------------------------------------------------
# Conversão
# --------------------------------------------------------------------------

def limpar_markdown(texto: str) -> str:
    """Remove ruídos que só gastam tokens, sem alterar o conteúdo."""
    import re

    # "# **Título**" -> "# Título" (títulos já são destacados)
    texto = re.sub(r"^(#{1,6} )\*\*(.+?)\*\*[ \t]*$", r"\1\2", texto, flags=re.MULTILINE)
    # espaços no fim das linhas
    texto = re.sub(r"[ \t]+$", "", texto, flags=re.MULTILINE)
    # no máximo uma linha em branco seguida
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip() + "\n"


def estimar_tokens(texto: str) -> int:
    # Aproximação comum: ~4 caracteres por token em textos em português/inglês.
    return max(1, len(texto) // 4)


def converter_pdf(
    pdf: Path,
    destino: Path,
    *,
    usar_ocr: bool,
    forcar_ocr: bool,
    idioma: str,
    dpi_ocr: int,
    manter_cabecalhos: bool,
    separar_paginas: bool,
) -> str:
    import pymupdf
    import pymupdf4llm

    with pymupdf.open(pdf) as doc:
        if doc.needs_pass:
            raise ValueError("o PDF está protegido por senha")
        markdown = pymupdf4llm.to_markdown(
            doc,
            use_ocr=usar_ocr,
            force_ocr=forcar_ocr,
            ocr_language=idioma,
            ocr_dpi=dpi_ocr,
            header=manter_cabecalhos,
            footer=manter_cabecalhos,
            page_separators=separar_paginas,
            show_progress=True,
        )

    markdown = limpar_markdown(markdown)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(markdown, encoding="utf-8", newline="\n")
    return markdown


def caminho_de_saida(pdf: Path, pasta_saida: Path | None) -> Path:
    pasta = pasta_saida if pasta_saida else pdf.parent
    return pasta / f"{pdf.stem}.md"


def criar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Converte PDFs em Markdown para usar com IAs generativas.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "exemplos:\n"
            "  python converter.py                       abre a janela de seleção\n"
            "  python converter.py apostila.pdf          gera apostila.md ao lado do PDF\n"
            "  python converter.py a.pdf b.pdf -o saida  gera os .md na pasta 'saida'\n"
            "  python converter.py prova.pdf --forcar-ocr\n"
        ),
    )
    p.add_argument("pdfs", nargs="*", type=Path, help="PDF(s) a converter (vazio = abrir janela)")
    p.add_argument("-o", "--saida", type=Path, help="pasta onde salvar os .md (padrão: mesma pasta do PDF)")
    p.add_argument("--idioma", default="por", help="idioma(s) do OCR no formato do Tesseract (padrão: por; ex.: por+eng)")
    p.add_argument("--sem-ocr", action="store_true", help="não usar OCR (mais rápido; páginas digitalizadas ficam vazias)")
    p.add_argument("--forcar-ocr", action="store_true", help="aplicar OCR em todas as páginas, mesmo as que já têm texto")
    p.add_argument("--dpi-ocr", type=int, default=300, help="resolução usada no OCR (padrão: 300; maior = mais preciso e mais lento)")
    p.add_argument("--manter-cabecalhos", action="store_true", help="manter cabeçalhos e rodapés repetidos das páginas")
    p.add_argument("--separar-paginas", action="store_true", help="inserir um separador entre as páginas")
    p.add_argument("-y", "--sobrescrever", action="store_true", help="sobrescrever .md existentes sem perguntar")
    return p


def main() -> int:
    args = criar_parser().parse_args()
    modo_janela = not args.pdfs

    pdfs = args.pdfs or escolher_pdfs_na_janela()
    if not pdfs:
        print("Nenhum arquivo selecionado.")
        return 1

    usar_ocr = not args.sem_ocr
    idioma = args.idioma
    if usar_ocr:
        usar_ocr, idioma = preparar_ocr(idioma)
    if args.forcar_ocr and not usar_ocr:
        print("AVISO: --forcar-ocr ignorado porque o OCR não está disponível.\n")

    print("Carregando o conversor...")
    import pymupdf4llm  # noqa: F401  (import demorado; feito uma única vez aqui)

    sucesso = 0
    for pdf in pdfs:
        print(f"\n=== {pdf.name} ===")
        if not pdf.is_file():
            print(f"ERRO: arquivo não encontrado: {pdf}")
            continue
        if pdf.suffix.lower() != ".pdf":
            print("ERRO: o arquivo não é um PDF.")
            continue

        destino = caminho_de_saida(pdf, args.saida)
        if destino.exists() and not args.sobrescrever:
            resposta = input(f"'{destino.name}' já existe. Sobrescrever? [s/N] ").strip().lower()
            if resposta not in ("s", "sim", "y"):
                print("Pulado.")
                continue

        inicio = time.perf_counter()
        try:
            markdown = converter_pdf(
                pdf,
                destino,
                usar_ocr=usar_ocr,
                forcar_ocr=args.forcar_ocr and usar_ocr,
                idioma=idioma,
                dpi_ocr=args.dpi_ocr,
                manter_cabecalhos=args.manter_cabecalhos,
                separar_paginas=args.separar_paginas,
            )
        except Exception as erro:
            print(f"ERRO ao converter: {erro}")
            continue

        duracao = time.perf_counter() - inicio
        tamanho_pdf = pdf.stat().st_size / 1024
        tamanho_md = destino.stat().st_size / 1024
        print(f"Salvo em: {destino}")
        print(
            f"Tempo: {duracao:.1f}s | PDF: {tamanho_pdf:,.0f} KB -> MD: {tamanho_md:,.0f} KB"
            f" | ~{estimar_tokens(markdown):,} tokens".replace(",", ".")
        )
        if len(markdown.strip()) < 50:
            print(
                "AVISO: quase nenhum texto extraído. Se o PDF for digitalizado,\n"
                "       instale o Tesseract (veja o README) ou use --forcar-ocr."
            )
        sucesso += 1

    print(f"\nConcluído: {sucesso} de {len(pdfs)} arquivo(s) convertido(s).")
    if modo_janela:
        input("\nPressione Enter para fechar...")
    return 0 if sucesso == len(pdfs) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(130)
