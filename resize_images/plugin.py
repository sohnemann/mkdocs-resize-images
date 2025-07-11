# Author: Jakub Andrýsek
# Email: email@kubaandrysek.cz
# Website: https://kubaandrysek.cz
# License: MIT
# GitHub: https://github.com/JakubAndrysek/mkdocs-resize-images
# PyPI: https://pypi.org/project/mkdocs-resize-images/
###################################################################
# Amended by: sohnemann 50672942+sohnemann@users.noreply.github.com
# GitHub: https://github.com/sohnemann

from pathlib import Path
from itertools import chain
from PIL import Image
import hashlib
import logging

from mkdocs.plugins import BasePlugin
from mkdocs.config import config_options

log: logging.Logger = logging.getLogger("mkdocs")

class ResizeImagesPlugin(BasePlugin):

	config_scheme = (
		('size', config_options.Type(list, default=(800, 600), required=False)),
		('source-dir', config_options.Type(str, default='assets-large', required=False)),
		('target-dir', config_options.Type(str, default='assets', required=False)),
		('extensions', config_options.Type(list, default=['.jpg', '.jpeg', '.png', '.gif', '.svg'], required=False)),
		('enable_cache', config_options.Type(bool, default=True, required=False)),
		('debug', config_options.Type(bool, default=False, required=False)),
		('recursive', config_options.Type(bool, default=True, required=False)),
	)

	def on_files(self, files, config):
		base_dir = Path(config['docs_dir'])
		for source_dir in base_dir.rglob(self.config['source-dir']):
			content_changed = False
			target_dir = source_dir.parent / self.config['target-dir']
			target_dir.mkdir(parents=True, exist_ok=True)

			hash_file_path = source_dir / '.resize-hash'
			existing_hashes = self.get_existing_hashes(hash_file_path)

			if self.config['recursive']:
				glob_func = source_dir.rglob
			else:
				glob_func = source_dir.glob

			for ext in self.config['extensions']:
				for file in chain(glob_func(f'*{ext.lower()}'), glob_func(f'*{ext.upper()}')):
					if not file.is_file():
						continue
					file_hash = self.get_file_hash(file)
					if not self.config['enable_cache'] or file_hash not in existing_hashes:
						content_changed = True
						self.resize_image(file, target_dir, source_dir)
						if self.config['debug']:
							log.info(f'Resized image {file} to {target_dir}')
						existing_hashes.append(file_hash)

			if content_changed:
				self.write_hashes(existing_hashes, hash_file_path)

		log.info(
			f"Resized images from `{self.config['source-dir']}` "
			f"to `{self.config['target-dir']}` with size {self.config['size']} "
			f"(recursive={self.config['recursive']})"
		)
		return files

	def resize_image(self, file, target_dir, source_dir):
		try:
			with Image.open(file) as img:
				tuple_size = tuple(self.config['size'])
				img.thumbnail(tuple_size)

				# Preserve subdirectory structure in target-dir
				relative_path = file.relative_to(source_dir)
				output_path = target_dir / relative_path
				output_path.parent.mkdir(parents=True, exist_ok=True)

				img.save(output_path)
		except Exception as e:
			log.error(f'Error resizing image {file}: {e}')

	def get_file_hash(self, filepath):
		with open(filepath, "rb") as f:
			bytes = f.read()
			readable_hash = hashlib.md5(bytes).hexdigest()
		return readable_hash

	def get_existing_hashes(self, hash_file_path):
		if hash_file_path.exists():
			with open(hash_file_path, 'r') as file:
				return file.read().splitlines()
		return []

	def write_hashes(self, hashes, hash_file_path):
		with open(hash_file_path, 'w') as file:
			for hash in hashes:
				file.write(f'{hash}\n')
