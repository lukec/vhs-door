package VHS;
use MooseX::Singleton;
use FindBin;
use Net::Twitter;
use YAML qw/LoadFile/;
use Fatal qw/rename/;
use Digest::SHA1 qw/sha1_hex/;
use WWW::Twitpic;
use namespace::clean -except => 'meta';

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
        print "DEBUG: tweet: '$msg'\n";
        return;
    }
    unless ( $nt->update($msg) ) {
        warn "Error sending tweet: " . $nt->http_message . "\n";
    }
    print "Sent tweet: $msg\n";
}

sub take_picture {
    my $self       = shift;
    my $now_hash   = sha1_hex(scalar localtime);
    my $short_hash = substr $now_hash, 0, 6;
    my $pic_base   = $self->config->{picture_base};
    my $filename   = "$pic_base/$short_hash.jpeg";
    system("streamer -c /dev/video0 -b 16 -o $filename");
    (my $short_name = $filename) =~ s#.+/(.+).jpeg#$1.jpg#;
    my $short_file = "$pic_base/$short_name";
    rename $filename => $short_file;

    my $pic_uri = "$pic_base/$short_name";
    print "\nSaved $short_file as $pic_uri\n";
    return $pic_uri;
}

sub _build_config {
    my $vhs_config_file = "$FindBin::Bin/../../.vhs.yaml";
    return LoadFile($vhs_config_file);
}



__PACKAGE__->meta->make_immutable;
1;
