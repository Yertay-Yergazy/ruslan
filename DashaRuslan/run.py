from app import create_app
from datetime import datetime

app = create_app()


@app.context_processor
def inject_globals():
    return {'now': datetime.utcnow()}


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='127.0.0.1', port=port)
