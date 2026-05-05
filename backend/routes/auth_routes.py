from backend.controllers import auth_controller


def register(router):
    router.add("POST", "/api/auth/register", auth_controller.register)
    router.add("POST", "/api/auth/login", auth_controller.login)
    router.add("GET", "/api/me", auth_controller.me)
