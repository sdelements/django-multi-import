from django.db import models


class Person(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    partner = models.ForeignKey('Person', null=True, related_name='person_partner')
    children = models.ManyToManyField('Person', related_name='person_children')

    @property
    def name(self):
        return self.first_name + ' ' + self.last_name