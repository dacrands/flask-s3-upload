from app import create_app, db
from app.models import User, File


app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'File': File,
    }
