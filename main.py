import os
import requests
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv

# Configurar a API key
load_dotenv()
# Ou use variável de ambiente:
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY nao encontrada. Configure na env")


def call_gemini(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": API_KEY
    }

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    else:
        return f"Erro: {response.status_code} - {response.text}"


# 1. Configurar a API do Gemini
# Substitua 'SUA_CHAVE_DE_API' pela sua chave real
# É uma boa prática armazenar a chave em uma variável de ambiente por segurança
genai.configure(api_key=API_KEY)

# Escolher o modelo que você quer usar

model = genai.GenerativeModel('gemini-1.5-pro')


def processar_csv_com_gemini(caminho_do_arquivo):
    """
    Processa um arquivo CSV usando a API do Gemini com base em um conjunto de regras.
    """
    try:
        # 2. Ler o arquivo CSV usando pandas
        df = pd.read_csv(caminho_do_arquivo)

        # Converter o DataFrame em uma string no formato CSV para enviar para a API
        dados_csv = df.to_csv(index=False)

        # 3. Construir um prompt detalhado
        # Este é o ponto mais importante. O prompt deve ser o mais claro possível
        # com todas as suas regras.

        regras = """
        Você é um assistente especializado em processamento de dados e deve otimizar o CSV a seguir.
        Siga as regras rigorosamente:
        
        1. **Simplificar:** A coluna 'produto' deve ser simplificada para remover descrições longas. Por exemplo, 'Notebook Dell XPS 15 9500 com Core i7' deve se tornar apenas 'Notebook Dell'.
        2. **Alterar Valor:** Na coluna 'preco', se o valor for maior que 2000, adicione '+impostos' no final. Exemplo: '3500' se torna '3500+impostos'.
        3. **Eliminar Colunas:** Remova as colunas 'id_transacao' e 'data_compra'.
        4. **Categorizar:** Adicione uma nova coluna chamada 'categoria' e atribua uma das seguintes categorias a cada linha com base na coluna 'produto':
           - Eletrônicos
           - Livros
           - Vestuário
           - Utensílios Domésticos
           - Outros
           A categoria 'Eletrônicos' se aplica a produtos como 'Notebook', 'Smartphone', 'Televisão'.
           A categoria 'Livros' se aplica a produtos como 'O Senhor dos Anéis', '1984'.
           A categoria 'Vestuário' se aplica a produtos como 'Camiseta', 'Calça Jeans'.
        
        Retorne apenas o novo CSV, sem nenhum texto adicional, cabeçalhos ou explicações, garantindo que o delimitador seja uma vírgula.
        """

        prompt = f"""
        {regras}

        CSV para processar:
        {dados_csv}
        """

        print("Enviando solicitação para a API do Gemini...")

        # 4. Enviar a solicitação para a API do Gemini
        # Aumentar o 'temperature' pode gerar respostas mais criativas, mas para processamento
        # de dados, um valor baixo (próximo de 0) é recomendado para maior precisão.

        # No caso de dados tabulares, é importante usar o 'generation_config'
        # para garantir que o modelo não retorne formatações indesejadas.

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0
            )
        )

        # 5. Processar a resposta e salvar o novo CSV
        csv_otimizado = response.text.strip()

        if csv_otimizado:
            # Salvar o novo CSV em um arquivo
            caminho_saida = "novo_dados_otimizados.csv"
            with open(caminho_saida, "w", encoding="utf-8") as f:
                f.write(csv_otimizado)

            print(
                f"Dados processados com sucesso! O novo CSV foi salvo em '{caminho_saida}'.")

            # Opcional: Ler o novo CSV com pandas para verificar o resultado
            df_otimizado = pd.read_csv(caminho_saida)
            print("\nPrévia do novo DataFrame:")
            print(df_otimizado.head())
        else:
            print("A API retornou uma resposta vazia. Tente ajustar o prompt.")

    except FileNotFoundError:
        print(f"Erro: O arquivo '{caminho_do_arquivo}' não foi encontrado.")
    except Exception as e:
        print(f"Ocorreu um erro: {e}")

# Exemplo de uso
# Crie um arquivo chamado 'dados.csv' com o seguinte conteúdo para testar:
# id_transacao,produto,preco,data_compra
# 1,"Notebook Dell XPS 15 9500 com Core i7",3500,"2025-09-20"
# 2,"O Senhor dos Anéis: A Sociedade do Anel",50,"2025-09-19"
# 3,"Calça Jeans Skinny Azul",120,"2025-09-18"
# 4,"Smartphone Samsung Galaxy S23",2500,"2025-09-17"
# 5,"Cadeira de Escritório Ergonômica",800,"2025-09-16"


# Em seguida, execute a função:
processar_csv_com_gemini('dados.csv')

# Exemplo de uso
if __name__ == "__main__":
    prompt = "Explain how AI works in a few words"
    resposta = call_gemini(prompt)
    print(resposta)
