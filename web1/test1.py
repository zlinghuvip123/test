class A():
    b = "123"
    def __init__(self):
        self.a = "aaa"

    def __getattr__(self, item):
        print("getattr is called!")
        value = ""
        if item == "test1":
            value = "test1-value"

        self.__dict__[item] = "test1-value"
        return value

    def test(self):
        pass


a_obj = A()
print(getattr(a_obj, "b"))
print(getattr(a_obj, "a"))

print(a_obj.a)
print(a_obj.b)
