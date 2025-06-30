def generate_blog(topic):
    from bloggen.main import run
    import tempfile
    import os
    from datetime import datetime

    # Create a temporary directory to store the generated blog file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Prepare inputs for the run function
        inputs = {
            'topic': topic,
            'current_year': str(datetime.now().year)
        }
        
        # Call the run function to generate the blog
        try:
            run(inputs)
            # Assuming the run function saves the blog to a file, return the file path
            generated_file_path = os.path.join(temp_dir, 'generated_blog.txt')
            return generated_file_path
        except Exception as e:
            raise Exception(f"An error occurred while generating the blog: {e}")
        
