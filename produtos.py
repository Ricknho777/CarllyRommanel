# produtos.py
import json
from datetime import datetime

class Produto:
    def __init__(self, 
                 id: int, 
                 code: str, 
                 name: str, 
                 price: float, 
                 image: str,
                 additional_images: list = None,
                 description: str = '',
                 features: list = None,
                 category: str = '',
                 sizes: list = None,
                 color: str = 'Prata',
                 gender: str = 'feminino',
                 on_sale: bool = False,
                 original_price: float = None,
                 discount_percentage: int = 0,
                 stock: int = 10,
                 created_at: str = None,
                 updated_at: str = None):
        
        self.id = id
        self.code = code
        self.name = name
        self.price = float(price)
        self.image = image
        self.additional_images = additional_images or []
        self.description = description
        self.features = features or []
        self.category = category
        self.sizes = sizes or [{"size": "Único", "available": True}]
        self.color = color
        self.gender = gender
        self.on_sale = bool(on_sale)
        
        if original_price is None:
            self.original_price = float(price)
        else:
            self.original_price = float(original_price)
            
        self.discount_percentage = int(discount_percentage)
        self.stock = int(stock)
        
        if created_at is None:
            self.created_at = datetime.now().isoformat()
        else:
            self.created_at = created_at
            
        if updated_at is None:
            self.updated_at = datetime.now().isoformat()
        else:
            self.updated_at = updated_at
    
    def to_dict(self):
        """Converte o produto para dicionário"""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'price': self.price,
            'image': self.image,
            'additional_images': self.additional_images,
            'description': self.description,
            'features': self.features,
            'category': self.category,
            'sizes': self.sizes,
            'color': self.color,
            'gender': self.gender,
            'on_sale': self.on_sale,
            'original_price': self.original_price,
            'discount_percentage': self.discount_percentage,
            'stock': self.stock,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Cria um Produto a partir de um dicionário"""
        return cls(
            id=data.get('id'),
            code=data.get('code'),
            name=data.get('name'),
            price=data.get('price', 0),
            image=data.get('image', ''),
            additional_images=data.get('additional_images', []),
            description=data.get('description', ''),
            features=data.get('features', []),
            category=data.get('category', ''),
            sizes=data.get('sizes', []),
            color=data.get('color', 'Prata'),
            gender=data.get('gender', 'feminino'),
            on_sale=data.get('on_sale', False),
            original_price=data.get('original_price'),
            discount_percentage=data.get('discount_percentage', 0),
            stock=data.get('stock', 10),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    def __str__(self):
        return f"Produto({self.id}: {self.name} - R$ {self.price:.2f})"
    
    def __repr__(self):
        return self.__str__()


class GerenciadorProdutos:
    def __init__(self):
        self.produtos = []
    
    def adicionar_produto(self, produto: Produto):
        """Adiciona um produto ao gerenciador"""
        self.produtos.append(produto)
    
    def remover_produto(self, produto_id: int) -> bool:
        """Remove um produto pelo ID"""
        initial_count = len(self.produtos)
        self.produtos = [p for p in self.produtos if p.id != produto_id]
        return len(self.produtos) < initial_count
    
    def buscar_por_id(self, produto_id: int):
        """Busca um produto pelo ID"""
        for produto in self.produtos:
            if produto.id == produto_id:
                return produto
        return None
    
    def buscar_por_codigo(self, codigo: str):
        """Busca um produto pelo código"""
        for produto in self.produtos:
            if produto.code == codigo:
                return produto
        return None
    
    def listar_por_categoria(self, categoria: str):
        """Lista produtos por categoria"""
        return [p for p in self.produtos if p.category == categoria]
    
    def listar_em_promocao(self):
        """Lista produtos em promoção"""
        return [p for p in self.produtos if p.on_sale]
    
    def atualizar_produto(self, produto_id: int, dados_atualizados: dict):
        """Atualiza um produto existente"""
        produto = self.buscar_por_id(produto_id)
        if not produto:
            return False
        
        for key, value in dados_atualizados.items():
            if hasattr(produto, key):
                setattr(produto, key, value)
        
        produto.updated_at = datetime.now().isoformat()
        return True
    
    def to_json(self):
        """Converte todos os produtos para JSON"""
        return [produto.to_dict() for produto in self.produtos]
    
    def salvar_para_arquivo(self, caminho_arquivo: str):
        """Salva todos os produtos em um arquivo JSON"""
        try:
            with open(caminho_arquivo, 'w', encoding='utf-8') as f:
                json.dump(self.to_json(), f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Erro ao salvar produtos: {str(e)}")
            return False
    
    def carregar_de_arquivo(self, caminho_arquivo: str):
        """Carrega produtos de um arquivo JSON"""
        try:
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                produtos_data = json.load(f)
            
            self.produtos.clear()
            for produto_data in produtos_data:
                produto = Produto.from_dict(produto_data)
                self.adicionar_produto(produto)
            
            return True
        except FileNotFoundError:
            print(f"Arquivo {caminho_arquivo} não encontrado")
            return False
        except Exception as e:
            print(f"Erro ao carregar produtos: {str(e)}")
            return False
    
    def __len__(self):
        return len(self.produtos)
    
    def __iter__(self):
        return iter(self.produtos)