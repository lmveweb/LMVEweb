from django import forms

from .models import MensajePatrocinio


class ContactoForm(forms.ModelForm):
    """Validación del formulario de Contacto.

    ModelForm para que los largos máximos salgan del modelo: el
    "maxlength" del HTML lo salta cualquier POST directo, y con Postgres
    un valor más largo tiraría un DataError no controlado.
    """

    # No se guarda en el modelo, pero el navegador ya la exige con
    # "required" y un POST directo se la puede saltar sin esfuerzo.
    acepta_politica = forms.BooleanField(
        error_messages={'required': 'Debes aceptar la Política de Privacidad para continuar.'},
    )

    class Meta:
        model = MensajePatrocinio
        fields = ['nombre', 'institucion', 'email', 'mensaje']
        error_messages = {
            'nombre': {
                'required': 'Falta el nombre y apellido.',
                'max_length': 'El nombre y apellido no puede superar los %(limit_value)d caracteres.',
            },
            'institucion': {
                'max_length': 'El nombre de la institución no puede superar los %(limit_value)d caracteres.',
            },
            'email': {
                'required': 'Falta el correo electrónico.',
                'invalid': 'El correo electrónico no es válido.',
                'max_length': 'El correo electrónico no puede superar los %(limit_value)d caracteres.',
            },
            'mensaje': {
                'required': 'Falta el mensaje.',
            },
        }

    def lista_errores(self):
        """Errores de todos los campos en una lista plana, en el orden del
        formulario: es lo que muestra el JavaScript de la página."""
        return [error for errores in self.errors.values() for error in errores]
