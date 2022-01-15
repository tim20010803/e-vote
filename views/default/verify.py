# import required libraries
import base64, rsa # install module with "pip install rsa".

# this is the ballot to verify
print("please clone all data and input here:")
a1 = input()
a2 = input()
a3 = input()
b = input()
c1 = input()
c2 = input()
c3 = input()
c4 = input()
c5 = input()

# this is the ballot to verify
ballot = (a1+'\n'+a2+'\n'+a3).strip()
print("a1 =" + a1+"\n")
print("a2 =" + a2+"\n")
print("a3 =" + a3+"\n")
print("ballot =" + ballot+"\n")
# this is the ballot RSA signature
signature = base64.b16decode(b)
print("b =" + b+"\n")
print("signature =" + str(signature)+"\n")
# this is the election public key
pk_pem = (c1+'\n'+c2+'\n'+c3+'\n'+c4+'\n'+c5)
public_key = rsa.PublicKey.load_pkcs1(pk_pem)
print("c1 =" + c1+"\n")
print("c2 =" + c2+"\n")
print("c3 =" + c3+"\n")
print("c4 =" + c4+"\n")
print("c5 =" + c5+"\n")
print("pk_pem =" + pk_pem+"\n")
print("public_key =" + str(public_key)+"\n")
# this is the code that verifies the signature

print()
try:
    if rsa.verify(ballot.encode(), signature, public_key):
        print('The result is valid')
    else:
        print('The result is invalid')
except:
    print('The result is invalid')