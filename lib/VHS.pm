package VHS;
use MooseX::Singleton;
use FindBin;
use Net::Twitter;
use namespace::clean -except => 'meta';
use YAML qw/LoadFile/;

has 'config' => (is => 'ro', lazy_build => 1);

# USAGE: use VHS;  VHS->send_tweet($msg, $url);
# $msg is your string
# $url is optional URL that will be appended if there is enough room

sub send_tweet {
    my $self = shift;
    my $msg  = shift;
    my $image_url = shift;

    if ($image_url and length($msg) < (140 - 1 + length $image_url)) {
        $msg .= " $image_url";
    }

    my $nt = Net::Twitter->new( 
        username => $self->config->{twitter_username},
        password => $self->config->{twitter_password},
        traits => ['WrapError', 'API::REST'],
    );
    if ($self->config->{debug}) {
        print "DEBUG - would have sent tweet\n";
        return;
    }
    unless ( $nt->update($msg) ) {
        warn "Error sending tweet: " . $nt->http_message . "\n";
    }
    print "Sent tweet!\n";
}


sub _build_config {
    my $vhs_config_file = "$FindBin::Bin/../../.vhs.yaml";
    return LoadFile($vhs_config_file);
}



__PACKAGE__->meta->make_immutable;
1;
