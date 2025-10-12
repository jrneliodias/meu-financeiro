import os
import sys
import sqlite3
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv

# Configurar a API key
load_dotenv()
# Ou use variável de ambiente:
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY nao encontrada. Configure na env")

# Configurar a API do Gemini
genai.configure(api_key=API_KEY)

# Escolher o modelo
model = genai.GenerativeModel('gemini-2.5-flash')


def get_expense_categories_from_db(db_path='db.sqlite3'):
    """
    Conecta ao banco SQLite e retorna todas as categorias do tipo 'expense'.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Buscar categorias do tipo 'expense'
        cursor.execute(
            "SELECT name FROM registers_category WHERE type = 'expense'")
        categories = [row[0] for row in cursor.fetchall()]

        conn.close()
        return categories
    except sqlite3.Error as e:
        print(f"Erro ao acessar o banco de dados: {e}")
        return []


def processar_csv_com_gemini(caminho_do_arquivo, caminho_saida=None):
    """
    Processa um arquivo CSV usando a API do Gemini para adicionar categorias
    baseadas nas categorias de despesas do banco de dados.
    """
    try:
        # 1. Buscar categorias do banco de dados
        print("Buscando categorias do banco de dados...")
        categorias = get_expense_categories_from_db()

        if not categorias:
            print("AVISO: Nenhuma categoria encontrada no banco de dados.")
            return

        print(f"Categorias encontradas: {', '.join(categorias)}")

        # 2. Ler o arquivo CSV usando pandas
        print(f"Lendo arquivo CSV: {caminho_do_arquivo}")
        df = pd.read_csv(caminho_do_arquivo)

        # Converter o DataFrame em uma string no formato CSV para enviar para a API
        dados_csv = df.to_csv(index=False)

        # 3. Construir um prompt detalhado com as categorias do banco
        categorias_lista = "\n           - ".join(categorias)

        regras = f"""
        Você é um assistente especializado em categorização de despesas financeiras.
        Siga as regras rigorosamente:

        1. **Categorizar:** Adicione uma nova coluna chamada 'category' (se ainda não existir) e atribua UMA das seguintes categorias a cada linha com base nos dados da linha (especialmente description, amount, e outras colunas disponíveis):
           - {categorias_lista}

        2. **Critérios de Categorização:**
           - Analise principalmente a coluna 'description' para identificar o tipo de despesa
           - Considere o contexto e palavras-chave na descrição
           - Use seu melhor julgamento para associar cada despesa à categoria mais apropriada
           - Se houver dúvida, escolha a categoria mais genérica que se aplique

        3. **Formato de Saída:**
           - Retorne APENAS o CSV completo com a coluna 'category' adicionada/atualizada
           - NÃO adicione texto explicativo, cabeçalhos adicionais ou formatação markdown
           - NÃO use crases (```) ou qualquer formatação de código
           - Use vírgula como delimitador
           - Mantenha todas as colunas originais do CSV

        Retorne apenas o CSV processado, começando diretamente com o cabeçalho.
        """

        prompt = f"""
        {regras}

        CSV para processar:
        {dados_csv}
        """

        print("Enviando solicitação para a API do Gemini...")

        # 4. Enviar a solicitação para a API do Gemini
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0
            )
        )

        # 5. Processar a resposta e salvar o novo CSV
        csv_otimizado = response.text.strip()

        # Remover possíveis marcadores de código markdown se existirem
        if csv_otimizado.startswith("```"):
            lines = csv_otimizado.split("\n")
            # Remove primeira e última linha se forem marcadores
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            csv_otimizado = "\n".join(lines)

        if csv_otimizado:
            # Determinar o caminho de saída
            if caminho_saida is None:
                # Adicionar '_processed' antes da extensão
                base, ext = os.path.splitext(caminho_do_arquivo)
                caminho_saida = f"{base}_processed{ext}"

            # Salvar o novo CSV em um arquivo
            with open(caminho_saida, "w", encoding="utf-8") as f:
                f.write(csv_otimizado)

            print(f"\nDados processados com sucesso!")
            print(f"CSV atualizado salvo em: {caminho_saida}")

            # Opcional: Ler o novo CSV com pandas para verificar o resultado
            try:
                df_otimizado = pd.read_csv(caminho_saida)
                print("\nPrévia do DataFrame processado:")
                print(df_otimizado.head())
                print(f"\nTotal de linhas: {len(df_otimizado)}")
                if 'category' in df_otimizado.columns:
                    print(f"\nCategorias atribuídas:")
                    print(df_otimizado['category'].value_counts())
            except Exception as e:
                print(f"Aviso: Não foi possível ler o CSV processado: {e}")
        else:
            print("A API retornou uma resposta vazia. Tente ajustar o prompt.")

    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_do_arquivo}' não foi encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")


# Exemplo de uso via linha de comando
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python main.py <caminho_do_csv> [caminho_saida_opcional]")
        print("\nExemplo:")
        print("  python main.py csvs/despesas.csv")
        print("  python main.py csvs/despesas.csv csvs/despesas_processado.csv")
        print("\nO script irá:")
        print("  1. Conectar ao banco db.sqlite3")
        print("  2. Buscar todas as categorias do tipo 'expense'")
        print("  3. Usar o Gemini para adicionar a coluna 'category' ao CSV")
        print("  4. Salvar o CSV processado (por padrão com sufixo '_processed')")
        sys.exit(1)

    caminho_csv = sys.argv[1]
    caminho_saida = sys.argv[2] if len(sys.argv) > 2 else None

    processar_csv_com_gemini(caminho_csv, caminho_saida)
