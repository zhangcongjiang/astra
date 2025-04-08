import json
import redis


class RedisInfo:
    # redis的相关配置 读取ini文件
    HOST_IP = "127.0.0.1"
    HOST_PORT = 6379
    PASSWORD = "nsf0cus."


# 连接池连接使用，节省了每次连接用的时间
class ControlRedis:
    conn_pool = redis.ConnectionPool(host=RedisInfo.HOST_IP, port=RedisInfo.HOST_PORT, password=RedisInfo.PASSWORD)

    def __init__(self):
        self.client = redis.Redis(connection_pool=self.conn_pool)

    @property
    def conn(self):
        return self.client

    def set_key(self, key, info):
        self.client.set(key, json.dumps(info))

    def get_key(self, key):
        value = self.client.get(key)
        return json.loads(value) if value else None

    def set_key_time(self, key, exp=10 * 60):
        self.client.expire(key, exp)

    def delete_key(self, key):
        if isinstance(key, str):
            self.client.delete(key)
        elif isinstance(key, tuple):
            self.client.delete(*key)

    def query_list(self, list_name, start=0, end=-1):
        all_list = self.client.lrange(name=list_name, start=start, end=end)
        return all_list

    def query_len(self, list_name):
        list_len = self.client.llen(name=list_name)
        return list_len

    def get_left_list(self, list_name):
        value = self.client.lpop(list_name)
        return json.loads(value) if value else None

    def add_right_list(self, list_name, info):
        self.client.rpush(list_name, json.dumps(info))

    def add_left_list(self, list_name, info):
        self.client.lpush(list_name, json.dumps(info))

    def set_lock(self, key, info, exp_time=10 * 60):
        if self.client.setnx(key, info):
            self.client.expire(key, exp_time)
            return True
        return False

    def exists_key(self, key):
        return self.client.exists(key)

    def set_hash_key(self, key, field, value):
        return self.client.hset(key, field, json.dumps(value))

    def get_hash_key(self, key, field):
        value = self.client.hget(key, field)
        return json.loads(value) if value else None

    def get_hash_all(self, key):
        all_value = self.client.hgetall(key)
        temp = {}
        if all_value:
            for k, v in all_value.items():
                k = k.decode()
                v = json.loads(v.decode())
                temp[k] = v
            return temp
        return None

    def del_hash_key(self, key, field):
        return self.client.hdel(key, field)

    def zaddlist(self, key, dict):
        pipe = self.client.pipeline()
        for member, score in dict.items():
            pipe.zadd(key, {member: score})
        pipe.execute()

    def zadd(self, key, score, member):
        return self.client.zadd(key, {score: member})

    def zscan(self, key):
        return self.client.zscan(key)

    def zrangebyscore(self, key, min, max):
        return self.client.zrangebyscore(key, min, max)

    def zremrangebyscore(self, key, start, end):
        return self.client.zremrangebyscore(key, start, end)
