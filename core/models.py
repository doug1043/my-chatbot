from __future__ import unicode_literals


from django.db import models

# Create your models here.

class Interaction(models.Model):
	input = models.CharField(max_length=100)
	output = models.TextField()

def __unicode__(self):
	return self.input

def get_output(self, binds):
	return self.output % binds

class Meta:
	db_table = 'interaction'

