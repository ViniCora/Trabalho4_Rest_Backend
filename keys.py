from Crypto.PublicKey import RSA
import os

# def generate_and_save_rsa_keypair():
#     key = RSA.generate(2048)
#     private_key = key.export_key()
#     with open("private.pem", "wb") as f:
#         f.write(private_key)

#     public_key = key.publickey().export_key()
#     with open("receiver.pem", "wb") as f:
#         f.write(public_key)

# Verificar se já existe uma folder para o Cliente - baseado no nome dele e criar as chaves se não existir
def valida_existencia_chaves(username: str):
    base_path = "Users"
    path = os.path.join(base_path, username)
    
    #Caso já exista ele simplesmente retorna para evitar ficar recriando
    if os.path.exists(path):
        #print(f"Pasta já existe, nenhuma chave gerada: {path}")
        return
    else:
        os.makedirs(path)
        #Gerar as chaves
        key = RSA.generate(2048)

        with open(os.path.join(path, "private.pem"), "wb") as f:
            f.write(key.export_key())

        with open(os.path.join(path, "public.pem"), "wb") as f:
            f.write(key.publickey().export_key())