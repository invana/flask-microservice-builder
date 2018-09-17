from flask_microservices_builder import MicroServiceBuilder

obj = MicroServiceBuilder(packages_file="microservices-example.json")
obj.generate_build()
