from app import create_app
import logging

log = logging.getLogger(__name__)

flask_app = create_app()

log.info("KeyShift starting up...")
if __name__ == '__main__':   
    flask_app.run(host='0.0.0.0', debug=True)
    