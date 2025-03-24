# from contextlib import asynccontextmanager
# import asyncio
#
# @asynccontextmanager
# async def async_resource_manager():
#     print("Acquiring resource")
#     yield "Resource"
#     # yield "Resource2"
#     # yield "Resource3"
#     print("Releasing resource")
#
# async def main():
#     async with async_resource_manager() as resource:
#         print(f"Using {resource}")
#
# asyncio.run(main())

# class MyClass:
#     count = 0  # 类属性
#
#     def __init__(self):
#         # MyClass.count += 1
#         self.count += 1
#
#     # @classmethod
#     # def get_count(cls):
#     #     return cls.count
#
# # 创建实例
# obj1 = MyClass()
# print(obj1.count)#1
# obj2 = MyClass()
# print(obj2.count)#2



# # 通过类调用类方法
# print(MyClass.get_count())  # 输出: 2
#
# # 通过实例调用类方法
# print(obj1.get_count())     # 输出: 2




class MyIterator:
    def __init__(self, data):
        self.data = data
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.data):
            raise StopIteration
        value = self.data[self.index]
        self.index += 1
        return value

# 使用
my_iter = MyIterator([1, 2, 3])
for item in my_iter:
    print(item)







