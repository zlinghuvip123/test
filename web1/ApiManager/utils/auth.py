import ldap
import traceback
def auth_user(user, passwd):
    conn = ldap.initialize("ldap://united-imaging.com:389/")
    try:
        conn.simple_bind_s(user, passwd)
        return 1
    except:
        traceback.print_exc()
        return 0