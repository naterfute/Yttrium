import argon2
from bcrypt import gensalt as _gensalt
from src.database import interactions
from sqlalchemy import Column

class hasher:

    _pwhasher = argon2.PasswordHasher()

    @classmethod
    async def hash_password(cls, password: str, salt: bytes):
        print(cls._pwhasher.hash(password=password, salt=salt))


    @classmethod
    async def verify_hash(
            cls,
            password: str,
            hashed_password: str | Column[str],
            salt: str | Column[str]
    ) -> bool:
        """
        Verify if a plaintext password matches the stored hashed password when using the given salt.
        
        This method hashes the provided password with the given salt and compares it against
        the stored hashed password. Returns 1 for a match, 0 for no match.

        Parameters:
        -----------
        password : str
            The plaintext password to verify
        hashed_password : str | Column[str]
            The stored hashed password to compare against
        salt : str | Column[str]
            The salt used in the original password hashing

        Returns:
        --------
        bool
            True if the hashed password matches the stored hash (verification successful)
            False if the hashed password doesn't match (verification failed)

        Example:
        --------
        >>> await MyClass.verify_hash("mypassword", stored_hash, stored_salt)
        True  # indicates successful verification
        """       

        if cls.hash_password(str(password), str.encode(str(salt))) == hashed_password:
            return True
        else:
            return False

    @classmethod
    async def redo_hash(cls, password):
        pass



class auth:
    @staticmethod
    async def gensalt(rounds: int = 12, prefix: bytes = b"2b") -> bytes:
        return _gensalt(rounds, prefix)
    
    @staticmethod
    async def verify_user(username, password):
        user = await interactions.fetchUser(username)
        if user == None:
            return "User does not exist"
        await hasher.verify_hash(password, user.password, user.salt)
        
