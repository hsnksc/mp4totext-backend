"""
Test kullanıcısının şifresini sıfırla
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Database URL
DATABASE_URL = "postgresql+asyncpg://dev_user:dev_password_123@localhost:5432/mp4totext_dev"

# Password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def reset_password():
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    # Create async session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # New password
    new_password = "Test1234!"
    hashed_password = pwd_context.hash(new_password)
    
    async with async_session() as session:
        # Update password
        result = await session.execute(
            f"""
            UPDATE users 
            SET hashed_password = '{hashed_password}'
            WHERE email = 'test@mp4totext.com'
            RETURNING id, email, full_name
            """
        )
        await session.commit()
        
        user = result.fetchone()
        if user:
            print(f"✅ Şifre sıfırlandı!")
            print(f"   Email: {user[1]}")
            print(f"   Name: {user[2]}")
            print(f"   Yeni Şifre: {new_password}")
        else:
            print("❌ Kullanıcı bulunamadı!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_password())
