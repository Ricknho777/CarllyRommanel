# produtos_data.py
from produtos import Produto

def criar_produtos_iniciais():
    """Cria uma lista de produtos iniciais para a loja"""
    produtos = [
        Produto(
            id=1,
            code="ROM001",
            name="Anel Aro Duplo Quadrado Banhado Ouro 18k",
            price=87.76,
            image="https://images.unsplash.com/photo-1605100804763-247f67b3557e",
            description="Anel elegante com design em aro duplo e acabamento banhado a ouro 18k.",
            features=["Banhado a Ouro 18k", "Design Quadrado Moderno", "Aro Duplo"],
            category="aneis",
            color="Dourado",
            gender="feminino",
            stock=15
        ),
        Produto(
            id=2,
            code="ROM002",
            name="Colar Coração com Pingente de Diamante",
            price=129.99,
            image="https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f",
            description="Colar delicado com pingente em forma de coração e diamante central.",
            features=["Pingente de Diamante", "Corrente Prata 925", "Fecho de Segurança"],
            category="colares",
            color="Prata",
            gender="feminino",
            stock=8
        ),
        Produto(
            id=3,
            code="ROM003",
            name="Brinco Argola Dourado Liso",
            price=45.50,
            image="https://images.unsplash.com/photo-1535632066927-ab7c9ab60908",
            description="Brinco argola em dourado liso, ideal para uso diário.",
            features=["Dourado 18k", "Argola 3cm", "Hipoalergênico"],
            category="brincos",
            color="Dourado",
            gender="feminino",
            stock=20
        ),
        Produto(
            id=4,
            code="ROM004",
            name="Pulseira Prata com Charms Personalizáveis",
            price=89.90,
            image="https://images.unsplash.com/photo-1584917865442-de89df76afd3",
            description="Pulseira em prata 925 com charms que podem ser personalizados.",
            features=["Prata 925", "Charms Inclusos", "Tamanho Ajustável"],
            category="pulseiras",
            color="Prata",
            gender="unissex",
            stock=12
        ),
        Produto(
            id=5,
            code="ROM005",
            name="Relógio Analógico Couro Marrom",
            price=199.99,
            image="https://images.unsplash.com/photo-1523170335258-f5ed11844a49",
            description="Relógio analógico elegante com pulseira de couro marrom.",
            features=["Movimento Quartz", "Couro Legítimo", "Resistente à Água"],
            category="relogios",
            color="Marrom",
            gender="masculino",
            stock=6
        ),
        Produto(
            id=6,
            code="PROM001",
            name="Kit Presente Anel + Brinco",
            price=99.99,
            original_price=150.00,
            discount_percentage=33,
            image="https://images.unsplash.com/photo-1536940137675-1ad8f3be7b8e",
            description="Kit especial presente contendo anel e brinco combinando.",
            features=["Kit Presente", "Embalagem Premium", "Garantia 1 Ano"],
            category="promocoes",
            color="Prata",
            gender="feminino",
            on_sale=True,
            stock=10
        ),
        Produto(
            id=7,
            code="ROM006",
            name="Anel Solitário Diamante 0.5ct",
            price=299.99,
            image="https://images.unsplash.com/photo-1598276628447-5fdcc44413c7",
            description="Anel solitário com diamante central de 0.5 quilates.",
            features=["Diamante 0.5ct", "Ouro 18k", "Garantia 2 anos"],
            category="solitarios",
            color="Branco",
            gender="feminino",
            stock=5
        ),
        Produto(
            id=8,
            code="PET001",
            name="Pingente Coração para Pet",
            price=39.90,
            image="https://images.unsplash.com/photo-1576201836106-db1758fd1c97",
            description="Pingente em formato de coração para coleira de pet.",
            features=["Aço Inoxidável", "Gravação Inclusa", "Tamanho Pequeno"],
            category="pet",
            color="Prata",
            gender="unissex",
            stock=25
        ),
        Produto(
            id=9,
            code="ROM007",
            name="Chaveiro Letra Inicial Prata",
            price=29.90,
            image="https://images.unsplash.com/photo-1590439471364-d6c8f5f3c815",
            description="Chaveiro personalizado com letra inicial em prata.",
            features=["Personalizável", "Prata 925", "Fecho Seguro"],
            category="chaveiros",
            color="Prata",
            gender="unissex",
            stock=30
        ),
        Produto(
            id=10,
            code="ALI001",
            name="Aliança Casal Ouro 18k",
            price=499.99,
            image="https://images.unsplash.com/photo-1531009134463-d36e9c8b9ec0",
            description="Par de alianças em ouro 18k para casal.",
            features=["Ouro 18k", "Par Completo", "Garantia Vitalícia"],
            category="aliancas",
            color="Dourado",
            gender="unissex",
            stock=4
        )
    ]
    
    return produtos
