from docx import Document

def gerar_contrato(dados):
    doc = Document("modelo.docx")

    # Exemplo
    for paragraph in doc.paragraphs:
        paragraph.text = paragraph.text.replace(
            "{{NOME_LOCATARIO}}",
            dados["nome_locatario"]
        )

    caminho = "contrato_preenchido.docx"
    doc.save(caminho)

    return caminho