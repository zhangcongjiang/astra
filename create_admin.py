#!/usr/bin/env python
"""
创建或检查管理员用户
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astra.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def main():
    print("检查和创建管理员用户...")
    
    # 检查用户是否存在
    try:
        user = User.objects.get(username='admin')
        print(f"✅ 用户已存在: {user.username}")
        print(f"   - ID: {user.id}")
        print(f"   - Email: {user.email}")
        print(f"   - 是否激活: {user.is_active}")
        print(f"   - 是否超级用户: {user.is_superuser}")
        
        # 测试密码
        auth_user = authenticate(username='admin', password='nsf0cus.')
        if auth_user:
            print("✅ 密码验证成功")
        else:
            print("❌ 密码验证失败，重置密码...")
            user.set_password('nsf0cus.')
            user.save()
            print("✅ 密码已重置")
            
    except User.DoesNotExist:
        print("❌ 用户不存在，创建新用户...")
        try:
            user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='nsf0cus.'
            )
            print(f"✅ 管理员用户创建成功: {user.username}")
        except Exception as e:
            print(f"❌ 创建用户失败: {e}")
            return
    
    # 最终验证
    final_user = authenticate(username='admin', password='nsf0cus.')
    if final_user:
        print("✅ 最终验证成功，用户可以正常登录")
    else:
        print("❌ 最终验证失败")

if __name__ == "__main__":
    main()