from django.db import models


class Chapter(models.Model):
    name = models.CharField(max_length=100)
    text = models.CharField(max_length=8000)


class Book(models.Model):
    name = models.CharField(max_length=100)
    author = models.ForeignKey('Person')
    chapters = models.ManyToManyField('Chapter')


class Person(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    partner = models.ForeignKey('Person',
                                null=True,
                                related_name='person_partner')

    children = models.ManyToManyField('Person',
                                      related_name='person_children')

    @property
    def name(self):
        return self.first_name + ' ' + self.last_name
