# src/solidus/db_router.py
class SolidusDBRouter:
    """
    Database router to allow potential future scaling with read replicas
    """

    def db_for_read(self, model, **hints):
        """Suggest the database to read from"""
        # For now, use default. Can be extended for read replicas
        return "default"

    def db_for_write(self, model, **hints):
        """Suggest the database for writes"""
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations between objects"""
        # Allow all relations for now
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure migrations only run on default database"""
        return db == "default"
