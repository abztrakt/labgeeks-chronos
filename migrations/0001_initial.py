# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Location'
        db.create_table('labgeeks_chronos_location', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
        ))
        db.send_create_signal('labgeeks_chronos', ['Location'])

        # Adding M2M table for field active_users on 'Location'
        db.create_table('labgeeks_chronos_location_active_users', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('location', models.ForeignKey(orm['labgeeks_chronos.location'], null=False)),
            ('user', models.ForeignKey(orm['auth.user'], null=False))
        ))
        db.create_unique('labgeeks_chronos_location_active_users', ['location_id', 'user_id'])

        # Adding model 'Punchclock'
        db.create_table('labgeeks_chronos_punchclock', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('location', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['labgeeks_chronos.Location'])),
            ('ip_address', self.gf('django.db.models.fields.IPAddressField')(max_length=15)),
        ))
        db.send_create_signal('labgeeks_chronos', ['Punchclock'])

        # Adding model 'Shift'
        db.create_table('labgeeks_chronos_shift', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('intime', self.gf('django.db.models.fields.DateTimeField')()),
            ('outtime', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('in_clock', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='in_punchclock', null=True, to=orm['labgeeks_chronos.Punchclock'])),
            ('out_clock', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='out_punchclock', null=True, to=orm['labgeeks_chronos.Punchclock'])),
            ('shiftnote', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('labgeeks_chronos', ['Shift'])


    def backwards(self, orm):
        
        # Deleting model 'Location'
        db.delete_table('labgeeks_chronos_location')

        # Removing M2M table for field active_users on 'Location'
        db.delete_table('labgeeks_chronos_location_active_users')

        # Deleting model 'Punchclock'
        db.delete_table('labgeeks_chronos_punchclock')

        # Deleting model 'Shift'
        db.delete_table('labgeeks_chronos_shift')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 16, 13, 15, 3, 381581)'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2012, 11, 16, 13, 15, 3, 381524)'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'labgeeks_chronos.location': {
            'Meta': {'object_name': 'Location'},
            'active_users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'labgeeks_chronos.punchclock': {
            'Meta': {'object_name': 'Punchclock'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['labgeeks_chronos.Location']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'labgeeks_chronos.shift': {
            'Meta': {'object_name': 'Shift'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_clock': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'in_punchclock'", 'null': 'True', 'to': "orm['labgeeks_chronos.Punchclock']"}),
            'intime': ('django.db.models.fields.DateTimeField', [], {}),
            'out_clock': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'out_punchclock'", 'null': 'True', 'to': "orm['labgeeks_chronos.Punchclock']"}),
            'outtime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'shiftnote': ('django.db.models.fields.TextField', [], {'blank': 'True'})
        }
    }

    complete_apps = ['labgeeks_chronos']
