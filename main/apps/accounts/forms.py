from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    """UserCreationForm apunta a auth.User; con un modelo de usuario propio
    (AUTH_USER_MODEL) hay que indicar el modelo explícitamente."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',)
