import object_storage
from cumulus.storage import CloudFilesStorage, CloudStorageDirectory
import mimetypes
import os, sys, logging
from cloudfiles.errors import NoSuchObject
from object_storage.errors import NotFound

from django.utils.deconstruct import deconstructible


@deconstructible
class SoftLayerStorage(CloudFilesStorage):

    """
    Custom storage for SoftLayer Cloud Files object storage.
    """
    default_quick_listdir = True
    logger = logging.getLogger('django-softlayer.debug')

    def _get_connection(self):
        if not hasattr(self, '_connection'):
            self._connection = object_storage.get_client(self.username, self.api_key, datacenter='dal05')
        return self._connection

    def _set_connection(self, value):
        self._connection = value

    connection = property(_get_connection, _set_connection)

    def _get_container(self):
        if not hasattr(self, '_container'):
            self.container = self.connection[self.container_name]
        return self._container

    def _set_container(self, container):
        """
        Set the container, making it publicly available if it is not already.
        """
        #        if not container.is_public():
        container.make_public()
        if hasattr(self, '_container_public_uri'):
            delattr(self, '_container_public_uri')
        self._container = container

    container = property(_get_container, _set_container)

    def _get_container_url(self):
        if not hasattr(self, '_container_public_uri'):
            if self.use_ssl:
                self._container_public_uri = self.container.url
            else:
                self._container_public_uri = self.container.url
        return self._container_public_uri

    container_url = property(_get_container_url)

    def _save(self, name, content):
        """
        Use the Cloud Files service to write ``content`` to a remote file
        (called ``name``).
        """
        (path, last) = os.path.split(name)
        if path:
            try:
                self.container.get_object(path)
            except (NoSuchObject, NotFound):
                self._save(path, CloudStorageDirectory(path))
            except:
                self.logger.debug('File saving unknown exception: %s' % sys.exc_info()[0])
                self.logger.debug('Error at filename: %s' % name)

        content.open()
        cloud_obj = self.container[name].create()
        if hasattr(content.file, 'size'):
            cloud_obj.size = content.file.size
        else:
            cloud_obj.size = content.size
            # If the content type is available, pass it in directly rather than
        # getting the cloud object to try to guess.
        if hasattr(content.file, 'content_type'):
            cloud_obj.content_type = content.file.content_type
        elif hasattr(content, 'content_type'):
            cloud_obj.content_type = content.content_type
        else:
            mime_type, encoding = mimetypes.guess_type(name)
            cloud_obj.content_type = mime_type
        cloud_obj.send(content)
        content.close()
        return name

    def size(self, name):
        """
        Returns the total size, in bytes, of the file specified by name.
        """
        return self._get_cloud_obj(name).props['size']

    def exists(self, name):
        """
        Returns True if a file referenced by the given name already exists in
        the storage system, or False if the name is available for a new file.
        """
        try:
            self._get_cloud_obj(name)
            return True
        except:
            return False

    def get_available_name(self, name):
        #=======================================================================
        # if self.exists(name):
        #     self.delete(name)
        #=======================================================================
        return name
    