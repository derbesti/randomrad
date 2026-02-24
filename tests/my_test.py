
import randomrad as rr

print(rr.current_backend())
print(rr.random())

rr.use_backend("hw", port="COM4")
print(rr.random())

rr.use_backend("file")
print(rr.random())

rr.use_backend("hw", port="COM4")
print(rr.random())
print(rr.choice([1,2,3,]))

print(rr.choices([1,2,3,5,7,9,11],5))

# for i in range(100):
#     print(rr.randint(0,100))
#
test=[]
for i in range(100):
    test.append(i)
rr.shuffle(test)
print(test)

print(rr.sample(test,50))
