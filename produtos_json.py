# criar_json.py
import json

produtos = [
    {
        "id": 1,
        "code": "54297500",
        "name": "Anel Aro Duplo Quadrado Banhado Ouro 18k",
        "price": 87.76,
        "image": "https://images.unsplash.com/photo-1605100804763-247f67b3557e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=600&q=80",
        "additionalImages": [
            "https://images.unsplash.com/photo-1605100804763-247f67b3557e?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=600&q=80",
            "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=600&q=80"
        ],
        "description": "Elegante anel aro duplo quadrado banhado à ouro 18k com zircônias.",
        "features": ["Banhado a ouro 18k", "Zircônias de alta qualidade", "Design duplo quadrado", "Acabamento premium"],
        "category": "aneis",
        "sizes": [
            {"size": "14", "available": True},
            {"size": "16", "available": True},
            {"size": "18", "available": True}
        ],
        "color": "Branco",
        "gender": "feminino",
        "onSale": False,
        "originalPrice": 87.76,
        "discountPercentage": 0
    },
]

# Salvar em arquivo JSON
with open('produtos.json', 'w', encoding='utf-8') as f:
    json.dump(produtos, f, ensure_ascii=False, indent=2)

print("Arquivo produtos.json criado com sucesso!")
print(f"{len(produtos)} produtos salvos.")
